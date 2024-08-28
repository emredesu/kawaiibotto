from commands.command import Command
from messagetypes import error, log
from globals import TWITCH_API_HEADERS, USERNAME as botUsername, GENSHIN_MYSQL_DB_HOST, GENSHIN_MYSQL_DB_USERNAME, GENSHIN_MYSQL_DB_PASSWORD, AUTHORIZED_USER, GENSHIN_DB_POOL_SIZE
import random
import requests
import mysql.connector
import mysql.connector.pooling
import traceback
import datetime
import json
import re
import asyncio

class GenshinCommand(Command):
    COMMAND_NAME = ["genshin"]
    COOLDOWN = 3
    DESCRIPTION = f"A fully fledged Genshin wish simulator with wish progress tracking, a primogem system and more! For all the commands, visit: https://emredesu.github.io/kawaiibotto/ paimonAYAYA"

    successfulInit = True

    requiredSecondsBetweenRedeems = 7200
    duelTimeout = 120
    tradeTimeout = 180

    primogemAmountOnRedeem = 648
    primogemAmountOnRegistration = 1600
    primogemDeductionPerLateInterval = 108

    wishCost = 160

    database = None
    cursor = None

    emojiAssociationGistLink = "https://gist.githubusercontent.com/emredesu/e13a6274d9ba9825562b279d00bb1c0b/raw/kawaiibottoGenshinEmojiAssociations.json"
    bannerIDLink = "https://operation-webstatic.mihoyo.com/gacha_info/hk4e/cn_gf01/gacha/list.json"
    bannerDataBaseLink = "https://operation-webstatic.hoyoverse.com/gacha_info/hk4e/os_euro/{}/en-us.json"

    validBannerNames = []
    bannerData = None
    bannerImageLinks = None

    emojiAssociations = None

    # ----- Wish math stuff -----
    characterBanner5StarHardPity = 90
    characterBanner5StarSoftPityStart = 75
    characterBanner4StarSoftPityStart = 9
    characterBanner4StarHardPity = 10

    weaponBanner5StarHardPity = 80
    weaponBanner5StarSoftPityStart = 63
    weaponBanner4StarSoftPityStart = 8
    weaponBanner4StarSoftPityChanceIncrease = 9
    weaponBanner4StarHardPity = 10

    standardBannerHardPity = 90
    standardBannerSoftPityStart = 75
    standardBanner4StarSoftPityStart = 9
    standardBanner4StarHardPity = 10

    characterBanner5StarRateUpProbability = 55
    characterBanner4StarRateUpProbability = 50

    weaponBanner5StarRateUpProbability = 75
    weaponBanner4StarRateUpProbability = 75

    # Character banner
    characterBanner5StarChance = 0.6
    characterBanner4StarChance = 5.1
    characterBanner4StarChanceWithSoftPity = 45

    # Weapon banner
    weaponBanner5StarChance = 0.7
    weaponBanner4StarChance = 6
    weaponBanner4StarChanceWithSoftPity8thRoll = 55
    weaponBanner4StarChanceWithSoftPity9thRoll = 95

    # Standard banner
    standardBanner5StarChance = 0.6
    standardBanner4StarChance = 5.1
    standardBanner4StarChanceWithSoftPity = 45

    # Bot emotes.
    sadEmote = "HungryPaimon 😭"
    danceEmote = "HungryPaimon DinoDance"
    loserEmote = "HungryPaimon 😈"
    shockedEmote = "HungryPaimon ⁉"
    tantrumEmote = "HungryPaimon 😑"
    angryEmote = "HungryPaimon 💢"
    primogemEmote = "HungryPaimon 💸"
    proudEmote = "HungryPaimon 🤗"
    deadEmote = "HungryPaimon 😵"
    neutralEmote = "HungryPaimon"
    shyEmote = "HungryPaimon 😳"
    ayayaEmote = "HungryPaimon ‼"
    derpEmote = "HungryPaimon ❓"
    nomEmote = "HungryPaimon 🍪"
    emergencyFoodEmote = "HungryPaimon 🍜"
    thumbsUpEmote = "HungryPaimon 👌"
    stabEmote = "HungryPaimon 🔪"

    # Roulette values
    rouletteWinChancePercentage = 45
    rouletteWinMultiplier = 1
    rouletteMinBet = 50

    # Slots values
    slotsElements = ["⭐", "HungryPaimon", "🌠", "🔥", "🌊", "🧊", "⚡", "⛰️", "🌪️", "🌵"]
    slotsWinMultiplier = 100
    slotsMinBet = 100

    # Banner data to be pulled.
    pulledBannerData = []

    def __init__(self, commands):
        super().__init__(commands)
        self.UpdateBannerData()

        try:
            self.dbConnectionPool = mysql.connector.pooling.MySQLConnectionPool(host=GENSHIN_MYSQL_DB_HOST, user=GENSHIN_MYSQL_DB_USERNAME, password=GENSHIN_MYSQL_DB_PASSWORD, database="genshinStats", pool_size=GENSHIN_DB_POOL_SIZE)
        except Exception as e:
            error(f"Fatal error while connecting to the database: {e.__class__.__name__}")
            traceback.print_exc()
            self.successfulInit = False
            
    def PullBannerData(self):
        self.pulledBannerData = []

        bannerIDRequest = requests.get(self.bannerIDLink)
        if bannerIDRequest.status_code != 200:
            raise Exception()
        
        for bannerData in bannerIDRequest.json()["data"]["list"]:
            # HACK: Ignore chronicle banner until we find a way to get the right gacha_id (current gacha_id returned is wrong for some reason)
            if bannerData["gacha_type"] == 500:
                continue

            bannerID = bannerData["gacha_id"]

            bannerDetailsRequest = requests.get(self.bannerDataBaseLink.format(bannerID))
            if bannerDetailsRequest.status_code != 200:
                raise Exception()
            
            self.pulledBannerData.append(bannerDetailsRequest.json())

    def UpdateBannerData(self):
        try:
            self.PullBannerData()
            self.bannerData = {}

            # We are supporting it in case they decide to add a third character banner, second weapon banner, second standard banner etc. because we can 8)
            _currCharacterBannerIndex = 0
            _currWeaponBannerIndex = 0
            _currStandardBannerIndex = 0

            for banner in self.pulledBannerData:
                if banner["gacha_type"] == 200: # Standard banner
                    name = "standard"

                    addedName = name
                    #addedName = name + str(_currStandardBannerIndex + 1) Let's keep this here in case they add a second standard banner.
                    _currStandardBannerIndex += 1

                    # Prepare the standard banner character containers.
                    self.bannerData[addedName] = {} 
                    self.bannerData[addedName]["all5StarCharacters"] = []
                    self.bannerData[addedName]["all5StarWeapons"] = []
                    self.bannerData[addedName]["all4StarCharacters"] = []
                    self.bannerData[addedName]["all4StarWeapons"] = []
                    self.bannerData[addedName]["all3StarWeapons"] = []

                    # Set up 5 star item containers, place the items in the correct container.
                    for item in banner["r5_prob_list"]:
                        if item["item_type"] == "Character":
                            self.bannerData[addedName]["all5StarCharacters"].append(item["item_name"])
                        elif item["item_type"] == "Weapon":
                            self.bannerData[addedName]["all5StarWeapons"].append(item["item_name"])
                    
                    # Set up 4 star item containers, place the items in the correct container.
                    for item in banner["r4_prob_list"]:
                        if item["item_type"] == "Character":
                            self.bannerData[addedName]["all4StarCharacters"].append(item["item_name"])
                        elif item["item_type"] == "Weapon":
                            self.bannerData[addedName]["all4StarWeapons"].append(item["item_name"])
                    
                    # Set up 3 star item container.
                    for item in banner["r3_prob_list"]:
                        self.bannerData[addedName]["all3StarWeapons"].append(item["item_name"])

                elif banner["gacha_type"] == 301 or banner["gacha_type"] == 400: # Character banner
                    name = "character"

                    addedName = name + str(_currCharacterBannerIndex + 1)
                    _currCharacterBannerIndex += 1

                    # Prepare the character banner character containers.
                    self.bannerData[addedName] = {}
                    self.bannerData[addedName]["rateUp5StarCharacter"] = ""
                    self.bannerData[addedName]["rateUp4StarCharacters"] = []
                    self.bannerData[addedName]["all5StarCharacters"] = []
                    self.bannerData[addedName]["all4StarCharacters"] = []
                    self.bannerData[addedName]["all4StarWeapons"] = []
                    self.bannerData[addedName]["all3StarWeapons"] = []

                    # Set up 5 star item containers, place the items in the correct container.
                    for item in banner["r5_prob_list"]:
                        if item["is_up"]:
                            self.bannerData[addedName]["rateUp5StarCharacter"] = item["item_name"]
                        else:
                            self.bannerData[addedName]["all5StarCharacters"].append(item["item_name"])
                    
                    # Set up 4 star item containers, place the items in the correct container.
                    for item in banner["r4_prob_list"]:
                        if item["item_type"] == "Character":
                            if item["is_up"]:
                                self.bannerData[addedName]["rateUp4StarCharacters"].append(item["item_name"])
                            else:
                                self.bannerData[addedName]["all4StarCharacters"].append(item["item_name"])
                        elif item["item_type"] == "Weapon":
                            self.bannerData[addedName]["all4StarWeapons"].append(item["item_name"])
                    
                    # Set up 3 star item container.
                    for item in banner["r3_prob_list"]:
                        self.bannerData[addedName]["all3StarWeapons"].append(item["item_name"])

                elif banner["gacha_type"] == 302: # Weapon banner
                    name = "weapon"

                    addedName = name
                    #addedName = name + str(_currWeaponBannerIndex + 1) Let's keep this here in case they add a second weapon banner.
                    _currWeaponBannerIndex += 1

                    self.bannerData[addedName] = {}
                    self.bannerData[addedName]["rateUp5StarWeapons"] = []
                    self.bannerData[addedName]["rateUp4StarWeapons"] = []
                    self.bannerData[addedName]["all5StarWeapons"] = []
                    self.bannerData[addedName]["all4StarCharacters"] = []
                    self.bannerData[addedName]["all4StarWeapons"] = []
                    self.bannerData[addedName]["all3StarWeapons"] = []

                    # Set up 5 star item containers, place the items in the correct container.
                    for item in banner["r5_prob_list"]:
                        if item["is_up"]:
                            self.bannerData[addedName]["rateUp5StarWeapons"].append(item["item_name"])
                        else:
                            self.bannerData[addedName]["all5StarWeapons"].append(item["item_name"])
                    
                    # Set up 4 star item containers, place the items in the correct container.
                    for item in banner["r4_prob_list"]:
                        if item["item_type"] == "Character":
                            self.bannerData[addedName]["all4StarCharacters"].append(item["item_name"])
                        elif item["item_type"] == "Weapon":
                            if item["is_up"]:
                                self.bannerData[addedName]["rateUp4StarWeapons"].append(item["item_name"])
                            else:
                                self.bannerData[addedName]["all4StarWeapons"].append(item["item_name"])
                    
                    # Set up the 3 star item container.
                    for item in banner["r3_prob_list"]:
                        self.bannerData[addedName]["all3StarWeapons"].append(item["item_name"])
                
            self.validBannerNames = [] # Clear before adding so that we don't add duplicates.

            for bannerName in self.bannerData:
                self.validBannerNames.append(bannerName)

            self.emojiAssociations = requests.get(self.emojiAssociationGistLink).json()
        except Exception as e:
            error(f"Fatal error while pulling data for the Genshin command: {e.__class__.__name__}")
            self.successfulInit = False

    def GetTwitchUserID(self, username: str) -> int:
        if type(username) is int: # There is a chance that we might already pass a userID to this command, if that's the case then just return the userID. Holy fucking spaghetti.
            return username

        url = f"https://api.twitch.tv/helix/users?login={username}"

        data = requests.get(url, headers=TWITCH_API_HEADERS).json()

        try:
            userid = data["data"][0]["id"]
            return int(userid)
        except IndexError:
            return -1

    def CheckUserRowExists(self, user) -> bool:
        userID = user if type(user) is int else self.GetTwitchUserID(user) # If we passed an int, it was already a userID so we don't need to query twitch. If we passed a str then it's a username, query Twitch for the userID.

        dbConn = self.dbConnectionPool.get_connection()
        dbCursor = dbConn.cursor()

        dbCursor.execute("SELECT * from wishstats where userId=%s", (userID,))

        result = dbCursor.fetchone()

        dbConn.close()

        return False if result is None else True

    def CreateUserTableEntry(self, username, uid):
        dbConn = self.dbConnectionPool.get_connection()
        dbCursor = dbConn.cursor()

        # Register on wishstats table
        # Subtracting two hours from the current time to allow the user to wish after getting registered. Give the user {self.primogemAmountOnRegistration} primogems on registration.
        dbCursor.execute("INSERT INTO wishstats VALUES (%s, %s, %s, 0, SUBTIME(NOW(), \"2:0:0\"), 0, 0, 0, 0, 0, FALSE, FALSE, FALSE, FALSE, \"{}\", \"{}\", \"{}\", \"{}\", 0, 0, 0)", (username, uid, self.primogemAmountOnRegistration))
        dbConn.commit()

        # Register on duelstats table
        dbCursor.execute("INSERT INTO duelstats VALUES (%s, %s, FALSE, 0, %s, FALSE, 0, 0, SUBTIME(NOW(), 1800))", (username, uid, "nobodyxd")) # dummy values
        dbConn.commit()

        # Register on the tradestats table
        dbCursor.execute("INSERT INTO tradestats VALUES (%s, %s, FALSE, FALSE, FALSE, %s, %s, %s, %s, 0, SUBTIME(NOW(), 1800), 0)", (username, uid, "nothingxd", "nostar",
                                                                                                                                     "noqual", "nobodyxd")) # dummy values
        dbConn.commit()

        dbCursor.execute("INSERT INTO gamblestats VALUES (%s, %s, 0, 0, 0, 0)", (username, uid))
        dbConn.commit()

        dbConn.close()

    # Returns the associated emoji(s) if it exists in the JSON, otherwise returns an empty string.
    def GetEmojiAssociation(self, item) -> str:
        try:
            return self.emojiAssociations[item]
        except KeyError:
            return ""

    # Get the current amount of primogems the user has based on the partitionValue. Partition value can be percentile values (50%), thousands values (10k) or the "all" keyword.
    def GetUserPrimogemsPartial(self, primogems: str, partitionValue: str) -> int:
        primogemAmount = int(primogems)

        # Parse the partitionValue.
        if partitionValue == "all":
            return primogemAmount
        elif partitionValue.endswith("%"):
            percentileValue = 0

            try:
                percentileValue = int(partitionValue[:-1:])
            except ValueError:
                return -1

            return round((primogemAmount / 100) * percentileValue)
        elif partitionValue.endswith("k") or partitionValue.endswith("K"):
            thousandsValue = 0

            try:
                thousandsValue = int(partitionValue[:-1:])
            except ValueError:
                return -1

            return thousandsValue * 1000
        else:
            return -1
        
    def CleanUpCommand(self, databaseConnection: mysql.connector.pooling.PooledMySQLConnection) -> None:
        databaseConnection.close()

    def execute(self, bot, messageData):
        if not self.successfulInit:
            bot.send_message(messageData.channel, f"This command has not been initialized properly... sorry! {self.emergencyFoodEmote}")
            return
        
        dbConnection = self.dbConnectionPool.get_connection()
        dbCursor = dbConnection.cursor()

        args = messageData.content.split()

        validFirstArgs = ["claim", "redeem", "wish", "characters", "weapons", "top", "register", "pity", "pitycheck", "pitycounter", "stats", "guarantee", "help", 
        "overview", "duel", "duelaccept", "dueldeny", "give", "giveprimos", "giveprimogems", "primogems", "primos", "points", "banner", "banners", "update", "gamble", "roulette", 
        "slots", "slot", "updatename"]

        firstArg = None
        try:
            firstArg = args[1]
        except IndexError:
            bot.send_message(messageData.channel, f"{messageData.user}, {self.DESCRIPTION}")
            return self.CleanUpCommand(dbConnection)

        if firstArg not in validFirstArgs:
            bot.send_message(messageData.channel, f"Invalid first argument supplied! Valid first arguments are: {' '.join(validFirstArgs)}")
            return self.CleanUpCommand(dbConnection)
    
        if firstArg in ["claim", "redeem"]:
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"])

            dbCursor.execute("SELECT primogems, lastRedeemTime FROM wishstats where userId=%s", (uid,))

            result = dbCursor.fetchone()
            ownedPrimogems = result[0]
            lastRedeemTime = result[1]

            timeNow = datetime.datetime.now()

            timePassed = timeNow - lastRedeemTime
            if int(timePassed.total_seconds()) > self.requiredSecondsBetweenRedeems:
                intervalsPassed = int(timePassed.total_seconds()) // self.requiredSecondsBetweenRedeems
                claimAmount = self.primogemAmountOnRedeem

                loopCount = intervalsPassed + 1

                for i in range(0, loopCount):
                    if i == 0:
                        continue

                    amountToBeAdded = self.primogemAmountOnRedeem - (self.primogemDeductionPerLateInterval * i)
                    
                    # Prevent the claim amount going into negatives.
                    if amountToBeAdded < 0:
                        amountToBeAdded = 0
                
                    # If we're on the current interval, the addition is done according to how many minutes have passed rather than the amount of intervals passed.
                    if i + 1 == loopCount and amountToBeAdded != 0:
                        minutesPassed = (int(timePassed.total_seconds()) - (intervalsPassed * self.requiredSecondsBetweenRedeems)) // 60
                        earningsPerMinuteThisInterval = amountToBeAdded / (self.requiredSecondsBetweenRedeems / 60)
                        amountToAddForThisInterval = int(minutesPassed * earningsPerMinuteThisInterval)
                        if amountToAddForThisInterval > amountToBeAdded:
                            amountToAddForThisInterval = amountToBeAdded
                        
                        claimAmount += amountToAddForThisInterval
                    else:
                        claimAmount += amountToBeAdded
                
                dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s, lastRedeemTime=NOW() WHERE userId=%s", (claimAmount, uid))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user}, you have successfully claimed {claimAmount} primogems! \
                You now have {ownedPrimogems + claimAmount} primogems! {self.primogemEmote}")
            else:
                timeUntilClaim = str(datetime.timedelta(seconds=self.requiredSecondsBetweenRedeems-int(timePassed.total_seconds())))
                bot.send_message(messageData.channel, f"{messageData.user}, you can't claim primogems yet - your next claim will be available in: {timeUntilClaim} {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

        elif firstArg == "wish":
            validSecondArgs = self.validBannerNames
            
            try:
                secondArg = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"Please provide a banner name to wish on. Current banner names are: {' '.join(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)

            if secondArg not in validSecondArgs:
                bot.send_message(messageData.channel, f"Please provide a valid banner name. Current valid banner names are: {' '.join(validSecondArgs)} | Example usage: _genshin wish {random.choice(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)
            
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            wishCount = 1
            try:
                wishCount = int(args[3]) # See if the user has supplied a third argument as how many wishes they want to make.
                if wishCount < 1:
                    bot.send_message(messageData.channel, f"{messageData.user}, don't mess with Paimon! You can't do {wishCount} wishes! {self.angryEmote}")
                    return self.CleanUpCommand(dbConnection)
                elif wishCount > 10:
                    bot.send_message(messageData.channel, f"{messageData.user}, you can't do more than 10 wishes at once! {self.angryEmote}")
                    return self.CleanUpCommand(dbConnection)
            except IndexError:
                pass
            except (ValueError, SyntaxError):
                bot.send_message(messageData.channel, f"{messageData.user}, \"{args[3]}\" is not an integer! {self.tantrumEmote} Example usage: _genshin wish {random.choice(validSecondArgs)} {random.randint(1, 10)}")
                return self.CleanUpCommand(dbConnection)

            isMultiWish = False if wishCount == 1 else True

            uid = int(messageData.tags["user-id"])

            dbCursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (uid,))
            ownedPrimogems = dbCursor.fetchone()[0]

            primogemCost = self.wishCost * wishCount

            if ownedPrimogems >= primogemCost:
                # Deduct primogems.
                dbCursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (primogemCost, uid,))
                dbConnection.commit()

                targetString = ""

                # ----- Character banner -----
                if "character" in secondArg:
                    for i in range(wishCount):
                        dbCursor.execute(f"SELECT characterBannerPityCounter, wishesSinceLast4StarOnCharacterBanner FROM wishstats where userId=%s", (uid,))
                        retrievedData = dbCursor.fetchone()
                        currentPityCounter = retrievedData[0]
                        wishesSinceLast4Star = retrievedData[1]

                        randomNumber = random.uniform(0, 100) # Roll a random float between 0 and 100.

                        currentFiveStarChance = self.characterBanner5StarChance

                        if currentPityCounter > self.characterBanner5StarSoftPityStart:
                            # For each wish above the soft pity counter, give the user an extra 5-7% chance of getting a 5 star.
                            for i in range(currentPityCounter - self.characterBanner5StarSoftPityStart):
                                currentFiveStarChance += random.uniform(5, 7)
                            
                        # Check if the user has gotten a 5 star.
                        userGotA5Star = randomNumber < currentFiveStarChance or currentPityCounter >= self.characterBanner5StarHardPity - 1

                        userGotA4Star = None
                        # If the user hasn't gotten a 5 star, check if they got a 4 star.
                        if not userGotA5Star:
                            currentFourStarChance = self.characterBanner4StarChance

                            # Soft pity check
                            if wishesSinceLast4Star + 1 == self.characterBanner4StarSoftPityStart:
                                currentFourStarChance = self.characterBanner4StarChanceWithSoftPity
                            # Hard pity check
                            elif wishesSinceLast4Star + 1 >= self.characterBanner4StarHardPity:
                                currentFourStarChance = 100
                            
                            userGotA4Star = randomNumber < currentFourStarChance

                        if userGotA5Star:
                            # We got a 5 star!

                            # Get data regarding to 5 star characters for the user.
                            dbCursor.execute("SELECT owned5StarCharacters, has5StarGuaranteeOnCharacterBanner FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = dbCursor.fetchone()

                            characterData = json.loads(retrievedData[0])
                            hasGuarantee = retrievedData[1]

                            rateUpWeaponRoll = random.uniform(0, 100)
                            if rateUpWeaponRoll < self.characterBanner5StarRateUpProbability or hasGuarantee:
                                # We got the banner character!
                                acquiredCharacter = self.bannerData[secondArg]["rateUp5StarCharacter"]
                                
                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you beat the 50-50" if not hasGuarantee else f"{messageData.user}, you used up your guarantee"
                                    targetString += f" and got {acquiredCharacter}(5🌟){self.GetEmojiAssociation(acquiredCharacter)}! {self.neutralEmote}"
                                else:
                                    targetString += f"| {acquiredCharacter}(5🌟)"

                                # Check if the user already has the character.
                                # If they have the character at C6, we'll give them a claim worth of primogems.
                                if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Add primogems to the user.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()
                                        
                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[C6💎] "
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newConstellation}⬆] "

                                # Finally, commit the final changes including guarantee and pity updates.
                                dbCursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=false, characterBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData) ,uid))
                                dbConnection.commit()

                                # 50-50 win/lose counting
                                if not hasGuarantee:
                                    dbCursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                    dbConnection.commit()

                            else:
                                # We lost the 5 star 50-50 :/
                                acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you lost your 50-50 and got {acquiredCharacter}(5🌟){self.GetEmojiAssociation(acquiredCharacter)}! {self.shockedEmote}"
                                else:
                                    targetString += f"| {acquiredCharacter}(5🌟)"

                                if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Give primogems to the user.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[C6💎] "
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newConstellation}⬆] "

                                # Finally, commit the final changes including guarantee and pity updates.
                                dbCursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=true, characterBannerPityCounter=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (json.dumps(characterData), uid))
                                dbConnection.commit()

                        elif userGotA4Star:
                            # We got a 4 star!

                            # Increment the pity counter.
                            dbCursor.execute("UPDATE wishstats SET characterBannerPityCounter=characterBannerPityCounter+1 WHERE userId=%s", (uid,))
                            dbConnection.commit()

                            # Get user info related to 4 stars.
                            dbCursor.execute("SELECT has4StarGuaranteeOnCharacterBanner, owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = dbCursor.fetchone()
                            hasGuarantee = retrievedData[0]
                            characterData = json.loads(retrievedData[1])

                            rateUpWeaponRoll = random.uniform(0, 100)
                            if rateUpWeaponRoll < self.characterBanner4StarRateUpProbability or hasGuarantee:
                                # We won the 4 star 50-50!

                                acquiredCharacter = random.choice(self.bannerData[secondArg]["rateUp4StarCharacters"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you won the 50-50" if not hasGuarantee else f"{messageData.user}, you used up your 4 star guarantee"
                                    targetString += f" and got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}!"
                                else:
                                    targetString += f"| {acquiredCharacter}(4⭐)"

                                if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Give primogems to the user.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[C6💎] "
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newConstellation}⬆]"

                                # Update the database with the final data.
                                dbCursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, has4StarGuaranteeOnCharacterBanner=false, wishesSinceLast4StarOnCharacterBanner=0 WHERE userId=%s",
                                (json.dumps(characterData), uid))
                                dbConnection.commit()

                                # 50-50 win/lose counting
                                if not hasGuarantee:
                                    dbCursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                    dbConnection.commit()

                            else:
                                # We lost the 4 star 50-50 :/

                                acquiredItem = random.choice(["weapon", "character"])
                                if acquiredItem == "weapon":
                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                    if not isMultiWish:
                                        targetString += f"{messageData.user}, you lost the 4 star 50-50 and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.shockedEmote}"
                                    else:
                                        targetString += f"| {acquiredWeapon}(4⭐)"

                                    dbCursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                    weaponData = json.loads(dbCursor.fetchone()[0])

                                    if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give user primogems if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            dbConnection.commit()

                                            if not isMultiWish:
                                                targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                            else:
                                                targetString += "[R5💎] "
                                        else:
                                            # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                            newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                            weaponData[acquiredWeapon] = newRefinement

                                            if not isMultiWish:
                                                targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                            else:
                                                targetString += f"[{newRefinement}⬆] "
                                        
                                    # Update the database with the new weapon.
                                    dbCursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                    dbConnection.commit()

                                else:
                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                    if not isMultiWish:
                                        targetString += f"You lost the 4 star 50-50 and got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}! {self.shockedEmote}"
                                    else:
                                        targetString += f"| {acquiredCharacter}(4⭐)"

                                    if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give user primogems.
                                            dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            dbConnection.commit()

                                            if not isMultiWish:
                                                targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                            else:
                                                targetString += "[C6💎] "
                                        else:
                                            # If they have the character but don't have them at C6, we'll give them a constellation.
                                            newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                            characterData[acquiredCharacter] = newConstellation

                                            if not isMultiWish:
                                                targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                            else:
                                                targetString += f"[{newConstellation}⬆] "
                                    
                                    # Update owned 4 star characters with the updated data.
                                    dbCursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                    dbConnection.commit()

                                # Finally, update the database data to have pity for the next 4 star.
                                dbCursor.execute("UPDATE wishstats SET has4StarGuaranteeOnCharacterBanner=true, wishesSinceLast4StarOnCharacterBanner=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (uid,))
                                dbConnection.commit()
                            
                        else:
                            acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                            # Increment the pity counters for 4 star and 5 star.
                            dbCursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnCharacterBanner=wishesSinceLast4StarOnCharacterBanner+1, characterBannerPityCounter=characterBannerPityCounter+1 WHERE userId=%s", (uid,))

                            if not isMultiWish:
                                targetString += f"{messageData.user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                            else:
                                targetString += f"| {acquiredTrash}(3★) "

                # ----- Standard banner -----                    
                elif "standard" in secondArg:
                    for i in range(wishCount):
                        dbCursor.execute("SELECT standardBannerPityCounter, wishesSinceLast4StarOnStandardBanner FROM wishstats where userId=%s", (uid,))
                        retrievedData = dbCursor.fetchone()
                        currentPityCounter = retrievedData[0]
                        wishesSinceLast4Star = retrievedData[1]

                        currentFiveStarChance = self.standardBanner5StarChance

                        if currentPityCounter > self.standardBannerSoftPityStart:
                            # For each wish above the soft pity counter, give the user an extra 5-7% chance of getting a 5 star.
                            for i in range(currentPityCounter - self.standardBannerSoftPityStart):
                                currentFiveStarChance += random.uniform(5, 7)

                        randomNumber = random.uniform(0, 100) # Roll a random float between 0 and 100.

                        # Check if the user has gotten a 5 star.
                        userGotA5Star = randomNumber < currentFiveStarChance or currentPityCounter >= self.standardBannerHardPity - 1

                        userGotA4Star = None
                        # If the user hasn't gotten a 5 star, check if they got a 4 star.
                        if not userGotA5Star:
                            currentFourStarChance = self.standardBanner4StarChance

                            # Soft pity check
                            if wishesSinceLast4Star + 1 == self.standardBanner4StarSoftPityStart:
                                currentFourStarChance = self.standardBanner4StarChanceWithSoftPity
                            # Hard pity check
                            elif wishesSinceLast4Star + 1 >= self.standardBanner4StarHardPity:
                                currentFourStarChance = 100
                            
                            userGotA4Star = randomNumber < currentFourStarChance

                        if userGotA5Star:
                            # We got a 5 star!
                            isCharacter = True if random.choice([0, 1]) == 0 else False
                            if isCharacter:
                                # Get info related to owned 5 star characters.
                                dbCursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = dbCursor.fetchone()
                                characterData = json.loads(retrievedData[0])

                                acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you got {acquiredCharacter}(5🌟){self.GetEmojiAssociation(acquiredCharacter)}! {self.neutralEmote}"
                                else:
                                    targetString += f"| {acquiredCharacter}(5🌟)"

                                if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[C6💎] "
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newConstellation}⬆] "

                                # Finally, commit the final changes including guarantee and pity updates.
                                dbCursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData), uid,))
                                dbConnection.commit()
                            else:
                                # Get info related to owned 5 star weapons.
                                dbCursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = dbCursor.fetchone()
                                weaponData = json.loads(retrievedData[0])

                                acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}! {self.neutralEmote}"
                                else:
                                    targetString += f"| {acquiredWeapon}(5🌟)"

                                if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Give out primogems if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[R5💎] "
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newRefinement}⬆] "
                                    
                                # Update the database with the new weapon.
                                dbCursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                dbConnection.commit()
                
                        elif userGotA4Star:
                            # We got a 4 star.

                            # Increment the pity counter.
                            dbCursor.execute("UPDATE wishstats SET standardBannerPityCounter=standardBannerPityCounter+1 WHERE userId=%s", (uid,))
                            dbConnection.commit()

                            isCharacter = True if random.choice([0, 1]) == 0 else False
                            if isCharacter:
                                # Get info related to owned 4 star characters.
                                dbCursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = dbCursor.fetchone()
                                characterData = json.loads(retrievedData[0])

                                acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}! {self.neutralEmote}"
                                else:
                                    targetString += f"| {acquiredCharacter}(4⭐)"

                                if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[C6💎] "
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newConstellation}⬆] "

                                # Finally, commit the final changes including guarantee and pity updates.
                                dbCursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(characterData), uid))
                                dbConnection.commit()
                            else:
                                # Get info related to owned 4 star weapons.
                                dbCursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = dbCursor.fetchone()
                                weaponData = json.loads(retrievedData[0])

                                acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.neutralEmote}"
                                else:
                                    targetString += f"| {acquiredWeapon}(4⭐)"

                                if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Reset wish timer if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[R5💎] "
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newRefinement}⬆] "
                                    
                                # Update the database with the new weapon.
                                dbCursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                dbConnection.commit()
                        else:
                            acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                            # Increment the pity counters for 5 star and 4 star.
                            dbCursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnStandardBanner=wishesSinceLast4StarOnStandardBanner+1, standardBannerPityCounter=standardBannerPityCounter+1 WHERE userId=%s", (uid,))

                            if not isMultiWish:
                                targetString += f"{messageData.user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                            else:
                                targetString += f"| {acquiredTrash}(3★) "

                # ----- Weapon banner -----
                else:
                    for i in range(wishCount):
                        # Get data regarding the weapon banner.
                        dbCursor.execute("SELECT weaponBannerPityCounter, has5StarGuaranteeOnWeaponBanner, has4StarGuaranteeOnWeaponBanner, wishesSinceLast4StarOnWeaponBanner from wishstats WHERE userId=%s", (uid,))
                        retrievedData = dbCursor.fetchone()
                        currentPityCounter = retrievedData[0]
                        hasGuarantee5Star = retrievedData[1]
                        hasGuarantee4Star = retrievedData[2]
                        wishesSinceLast4Star = retrievedData[3]

                        currentFiveStarChance = self.weaponBanner5StarChance

                        if currentPityCounter > self.weaponBanner5StarSoftPityStart:
                            # For each wish above the soft pity counter, give the user an extra 5-7% chance of getting a 5 star.
                            for i in range(currentPityCounter - self.weaponBanner5StarSoftPityStart):
                                currentFiveStarChance += random.uniform(5, 7)

                        randomNumber = random.uniform(0, 100) # Roll a random float between 0 and 100.

                        # Check if the user has gotten a 5 star.
                        userGotA5Star = randomNumber < currentFiveStarChance or currentPityCounter >= self.weaponBanner5StarHardPity - 1

                        userGotA4Star = None
                        # If the user hasn't gotten a 5 star, check if they got a 4 star.
                        if not userGotA5Star:
                            currentFourStarChance = self.weaponBanner4StarChance

                            # Soft pity check
                            if wishesSinceLast4Star + 1 == self.weaponBanner4StarSoftPityStart:
                                currentFourStarChance = self.weaponBanner4StarChanceWithSoftPity8thRoll
                            elif wishesSinceLast4Star + 1 == self.weaponBanner4StarSoftPityChanceIncrease:
                                currentFourStarChance = self.weaponBanner4StarChanceWithSoftPity9thRoll
                            # Hard pity check
                            elif wishesSinceLast4Star + 1 >= self.weaponBanner4StarHardPity:
                                currentFourStarChance = 100
                            
                            userGotA4Star = randomNumber < currentFourStarChance

                        if userGotA5Star:
                            # We got a 5 star!

                            # Get data related to the owned 5 star weapons
                            dbCursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                            weaponData = json.loads(dbCursor.fetchone()[0])

                            # Roll a random chance or see if we have guarantee to check if the 5 star we got is one of the featured ones.
                            if random.uniform(0, 100) < self.weaponBanner5StarRateUpProbability or hasGuarantee5Star:
                                # We got one of the featured weapons!
                                acquiredWeapon = random.choice(self.bannerData[secondArg]["rateUp5StarWeapons"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you beat the odds of 75-25" if not hasGuarantee5Star else f"{messageData.user}, you used up your guarantee"
                                    targetString += f" and got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}!"
                                else:
                                    targetString += f"| {acquiredWeapon}(5🌟)"

                                if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Give the user primogems if the weapon was already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[R5💎] "
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newRefinement}⬆] "
                                    
                                # Update the database with the new weapon.
                                dbCursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=false, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                dbConnection.commit()
                            else:
                                # We lost the 75-25.
                                acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, You lost the 75-25 and got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}! {self.shockedEmote}"
                                else:
                                    targetString += f"| {acquiredWeapon}(5🌟)"

                                if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Give the user primogems if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[R5💎] "
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement
                                        
                                        if not isMultiWish:
                                            targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newRefinement}⬆] "
                                    
                                # Update the database with the new weapon.
                                dbCursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=true, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid,))
                                dbConnection.commit()

                        elif userGotA4Star:
                            # We got a 4 star.

                            # Increment the pity counter.
                            dbCursor.execute("UPDATE wishstats SET weaponBannerPityCounter=weaponBannerPityCounter+1 WHERE userId=%s", (uid,))
                            dbConnection.commit()
                            
                            # Get user info related to 4 stars.
                            dbCursor.execute("SELECT has4StarGuaranteeOnWeaponBanner, owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = dbCursor.fetchone()
                            hasGuarantee = retrievedData[0]
                            weaponData = json.loads(retrievedData[1])

                            rateUpWeaponRoll = random.uniform(0, 100)
                            if rateUpWeaponRoll < self.weaponBanner4StarRateUpProbability or hasGuarantee4Star:
                                # We won the 4 star 50-50!

                                acquiredWeapon = random.choice(self.bannerData[secondArg]["rateUp4StarWeapons"])

                                if not isMultiWish:
                                    targetString = f"{messageData.user}, you won the 50-50" if not hasGuarantee else f"{messageData.user}, you used up your 4 star guarantee"
                                    targetString += f" and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}!"
                                else:
                                    targetString += f"| {acquiredWeapon}(4⭐)"

                                if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Give the user primogems if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Give user primogems.
                                        dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                        dbConnection.commit()

                                        if not isMultiWish:
                                            targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                        else:
                                            targetString += "[R5💎] "
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        if not isMultiWish:
                                            targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                        else:
                                            targetString += f"[{newRefinement}⬆] "

                                # Update the database with the final data.
                                dbCursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, has4StarGuaranteeOnWeaponBanner=false, wishesSinceLast4StarOnWeaponBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                dbConnection.commit()
                            else:
                                # We lost the 4 star 50-50 :/

                                acquiredItem = random.choice(["weapon", "character"])
                                if acquiredItem == "weapon":
                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{messageData.user}, you lost the 4 star 50-50"
                                        targetString += f" and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.sadEmote}"
                                    else:
                                        targetString += f"| {acquiredWeapon}(4⭐)"

                                    dbCursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                    weaponData = json.loads(dbCursor.fetchone()[0])

                                    if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give the user primogems if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            dbConnection.commit()

                                            if not isMultiWish:
                                                targetString += f" However, you already had {acquiredWeapon} at R5 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                            else:
                                                targetString += "[R5💎] "
                                        else:
                                            # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                            newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                            weaponData[acquiredWeapon] = newRefinement

                                            if not isMultiWish:
                                                targetString += f" Your {acquiredWeapon} is now {newRefinement}! {self.proudEmote}"
                                            else:
                                                targetString += f"[{newRefinement}⬆] "
                                        
                                    # Update the database with the new weapon.
                                    dbCursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                    dbConnection.commit()
                                else:
                                    dbCursor.execute("SELECT owned4StarCharacters from wishstats WHERE userId=%s", (uid,))
                                    characterData = json.loads(dbCursor.fetchone()[0])

                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                    if not isMultiWish:
                                        targetString += f" and got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}! {self.tantrumEmote}"
                                    else:
                                        targetString += f"| {acquiredCharacter}(4⭐)"

                                    if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give the user primogems.
                                            dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            dbConnection.commit()

                                            if not isMultiWish:
                                                targetString += f" However, you already had {acquiredCharacter} at C6 before, so you get {self.primogemAmountOnRedeem} primogems instead. {self.proudEmote}"
                                            else:
                                                targetString += "[C6💎] "
                                        else:
                                            # If they have the character but don't have them at C6, we'll give them a constellation.
                                            newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                            characterData[acquiredCharacter] = newConstellation

                                            if not isMultiWish:
                                                targetString += f" Your {acquiredCharacter} is now {newConstellation}! {self.proudEmote}"
                                            else:
                                                targetString += f"[{newConstellation}⬆] "
                                    
                                    # Update owned 4 star characters with the updated data.
                                    dbCursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                    dbConnection.commit()

                                # Finally, update the database data to have pity for the next 4 star.
                                dbCursor.execute("UPDATE wishstats SET has4StarGuaranteeOnWeaponBanner=true, wishesSinceLast4StarOnWeaponBanner=0 WHERE userId=%s", (uid,))
                                dbConnection.commit()                        
                        else:
                            acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                            # Increment the pity counters for 4 star and 5 star.
                            dbCursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnWeaponBanner=wishesSinceLast4StarOnWeaponBanner+1, weaponBannerPityCounter=weaponBannerPityCounter+1 WHERE userId=%s", (uid,))

                            if not isMultiWish:
                                targetString += f"{messageData.user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                            else:
                                targetString += f"| {acquiredTrash}(3★) "
            else:
                bot.send_message(messageData.channel, f"{messageData.user}, you need {primogemCost} primogems for that, but you have {ownedPrimogems}! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            # Increase the user's wish counter.
            dbCursor.execute("UPDATE wishstats SET wishesDone=wishesDone+%s WHERE userId=%s", (wishCount, uid))
            dbConnection.commit()

            bot.send_message(messageData.channel, (messageData.user + ", " if isMultiWish else "") + targetString)
        elif firstArg == "characters":
            validSecondArgs = ["4star", "5star"]
            secondArg = None

            targetUser = int(messageData.tags["user-id"])

            try:
                secondArg = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"Please provide a character type to retrieve. Character types are: {' '.join(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)
            
            try:
                targetUser = args[3]
            except IndexError:
                pass

            targetUser = targetUser.strip("@,") if type(targetUser) is str else targetUser

            addressingMethod = "you" if targetUser == messageData.user else "they"

            if secondArg not in validSecondArgs:
                bot.send_message(messageData.channel, f"Please provide a valid character type. Valid character types are: {' '.join(validSecondArgs)} | Example usage: _genshin characters {random.choice(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)
            
            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            else:
                uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

                if secondArg == "5star":
                    dbCursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                    characterData = json.loads(dbCursor.fetchone()[0])

                    if len(characterData.items()) == 0:
                        bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} have no 5 star characters to show. {self.deadEmote}")
                        return self.CleanUpCommand(dbConnection)

                    targetString = ""

                    currentLoopCount = 0
                    for key, pair in characterData.items():
                        currentLoopCount += 1

                        targetString += f"{key} ({pair})"
                        
                        if currentLoopCount < len(characterData.items()):
                            targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                    
                    bot.send_message(messageData.channel, f"{messageData.user}, {targetString}")
                else:
                    dbCursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                    characterData = json.loads(dbCursor.fetchone()[0])

                    if len(characterData.items()) == 0:
                        bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} have no 4 star characters to show. {self.deadEmote}")
                        return self.CleanUpCommand(dbConnection)

                    targetString = ""

                    currentLoopCount = 0
                    for key, pair in characterData.items():
                        currentLoopCount += 1

                        targetString += f"{key} ({pair})"
                        
                        if currentLoopCount < len(characterData.items()):
                            targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                    
                    bot.send_message(messageData.channel, f"{messageData.user}, {targetString}")
        elif firstArg == "weapons":
            validSecondArgs = ["4star", "5star"]
            secondArg = None

            targetUser = int(messageData.tags["user-id"])

            try:
                secondArg = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"Please provide a weapon type to retrieve. Valid weapon types are: {' '.join(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)
            
            try:
                targetUser = args[3]
            except IndexError:
                pass

            targetUser = targetUser.strip("@,") if type(targetUser) is str else targetUser

            addressingMethod = "you" if targetUser == messageData.user else "they"

            if secondArg not in validSecondArgs:
                bot.send_message(messageData.channel, f"Please provide a valid weapon type. Valid weapon types are: {' '.join(validSecondArgs)} | Example usage: _genshin weapons {random.choice(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)

            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)
        
            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            else:
                uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

                if secondArg == "5star":
                    dbCursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                    weaponData = json.loads(dbCursor.fetchone()[0])

                    if len(weaponData.items()) == 0:
                        bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} have no 5 star weapons to show. {self.deadEmote}")
                        return self.CleanUpCommand(dbConnection)

                    targetString = ""

                    currentLoopCount = 0
                    for key, pair in weaponData.items():
                        currentLoopCount += 1

                        targetString += f"{key} ({pair})"
                        
                        if currentLoopCount < len(weaponData.items()):
                            targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                    
                    bot.send_message(messageData.channel, f"{messageData.user}, {targetString}")
                else:
                    dbCursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                    weaponData = json.loads(dbCursor.fetchone()[0])

                    if len(weaponData.items()) == 0:
                        bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} have no 4 star weapons to show. {self.deadEmote}")
                        return self.CleanUpCommand(dbConnection)

                    targetString = ""

                    currentLoopCount = 0
                    for key, pair in weaponData.items():
                        currentLoopCount += 1

                        targetString += f"{key} ({pair})"
                        
                        if currentLoopCount < len(weaponData.items()):
                            targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                    
                    bot.send_message(messageData.channel, f"{messageData.user}, {targetString}")
        elif firstArg in ["primogems", "primos", "points"]:
            targetUser = int(messageData.tags["user-id"])
            try:
                targetUser = args[2]
            except IndexError:
                pass

            targetUser = targetUser.strip("@,") if type(targetUser) is str else targetUser

            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {'you are not registered!' if targetUser == messageData.user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

            # Pull primogem data from the database.
            dbCursor.execute("SELECT primogems, \
                                (SELECT COUNT(*)+1 FROM wishstats WHERE primogems>x.primogems) AS rankUpper, \
                                (SELECT COUNT(*) FROM wishstats WHERE primogems>=x.primogems) AS rankLower, \
                                (SELECT COUNT(*) FROM wishstats) AS userCount \
                                FROM `wishstats` x WHERE x.userId=%s", (uid,))
            data = dbCursor.fetchone()
            userPrimogems = data[0]
            userRankUpper = data[1]
            userRankLower = data[2]
            userCount = data[3]

            addressingMethod = "you" if targetUser == messageData.user else "they"

            bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} have {userPrimogems} primogems and are placed {userRankUpper}/{userCount}. {self.nomEmote}")

        elif firstArg == "top":
            validSecondArgs = ["wishes", "fiftyfiftieswon", "fiftyfiftieslost", "primogems", "primos", "points", "rouletteswon", "rouletteslost", "slotswon", "slotslost"]
            secondArg = None

            try:
                secondArg = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"{messageData.user}, please provide a second argument to get the top stats for! Valid second arguments are: {' '.join(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)

            if secondArg not in validSecondArgs:
                bot.send_message(messageData.channel, f"{messageData.user}, please provide a valid second second argument to get the top stats for! Valid second arguments are: {' '.join(validSecondArgs)}")
                return self.CleanUpCommand(dbConnection)

            if secondArg == "wishes":
                dbCursor.execute("SELECT username, wishesDone FROM wishstats ORDER BY wishesDone DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                
                bot.send_message(messageData.channel, targetStr)
            elif secondArg == "fiftyfiftieswon":
                dbCursor.execute("SELECT username, fiftyFiftiesWon FROM wishstats ORDER BY fiftyFiftiesWon DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                
                bot.send_message(messageData.channel, targetStr)
            elif secondArg == "fiftyfiftieslost":
                dbCursor.execute("SELECT username, fiftyFiftiesLost FROM wishstats ORDER BY fiftyFiftiesLost DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                
                bot.send_message(messageData.channel, targetStr)
            elif secondArg in ["primogems", "primos", "points"]:
                dbCursor.execute("SELECT username, primogems FROM wishstats ORDER BY primogems DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                
                bot.send_message(messageData.channel, targetStr)
            elif secondArg in "rouletteswon":
                dbCursor.execute("SELECT username, roulettesWon FROM gamblestats ORDER BY roulettesWon DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                bot.send_message(messageData.channel, targetStr)
            elif secondArg in "rouletteslost":
                dbCursor.execute("SELECT username, roulettesLost FROM gamblestats ORDER BY roulettesLost DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                bot.send_message(messageData.channel, targetStr)
            elif secondArg in "slotswon":
                dbCursor.execute("SELECT username, slotsWon FROM gamblestats ORDER BY slotsWon DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                bot.send_message(messageData.channel, targetStr)
            elif secondArg in "slotslost":
                dbCursor.execute("SELECT username, slotsLost FROM gamblestats ORDER BY slotsLost DESC LIMIT 10")
                result = dbCursor.fetchmany(10)

                targetStr = ""

                currentLoopCount = 0
                for data in result:
                    currentLoopCount += 1

                    targetStr += f"{data[0]}_({data[1]})"
                    if currentLoopCount < len(result):
                        targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                bot.send_message(messageData.channel, targetStr)

        elif firstArg in ["pity", "pitycheck", "pitycounter"]:
            targetUser = int(messageData.tags["user-id"])
            try:
                targetUser = args[2]
            except IndexError:
                pass

            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {'you' if targetUser == messageData.user else 'they'} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

            dbCursor.execute("SELECT characterBannerPityCounter, weaponBannerPityCounter, standardBannerPityCounter, wishesSinceLast4StarOnCharacterBanner, \
            wishesSinceLast4StarOnWeaponBanner, wishesSinceLast4StarOnStandardBanner FROM wishstats WHERE userId=%s", (uid,))
            results = dbCursor.fetchone()

            addressingMethod = "Your" if targetUser == messageData.user else "Their"

            bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} current pity counters - Character: {results[0]} | Weapon: {results[1]} | Standard: {results[2]} {self.neutralEmote} \
            Wishes since last 4 star - Character: {results[3]} | Weapon: {results[4]} | Standard: {results[5]} {self.primogemEmote}")
        elif firstArg == "stats":
            targetUser = int(messageData.tags["user-id"])
            try:
                targetUser = args[2]
            except IndexError:
                pass

            targetUser = targetUser.strip("@,") if type(targetUser) is str else targetUser

            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {'you are not registered!' if targetUser == messageData.user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

            dbCursor.execute("SELECT wishesDone, fiftyFiftiesWon, fiftyFiftiesLost, owned5StarCharacters, owned5StarWeapons, owned4StarCharacters, owned4StarWeapons, primogems FROM wishstats WHERE userId=%s", (uid,))
            results = dbCursor.fetchone()

            wishesDone = results[0]
            fiftyFiftiesWon = results[1]
            fiftyFiftiesLost = results[2]
            owned5StarCharacters = json.loads(results[3])
            owned5StarWeapons = json.loads(results[4])
            owned4StarCharacters = json.loads(results[5])
            owned4StarWeapons = json.loads(results[6])
            userPrimogems = results[7]

            dbCursor.execute("SELECT tradesDone FROM tradestats WHERE userId=%s", (uid,))
            tradesDone = dbCursor.fetchone()[0]

            dbCursor.execute("SELECT duelsWon, duelsLost FROM duelstats WHERE userId=%s", (uid,))
            duelData = dbCursor.fetchone()
            duelsWon = duelData[0]
            duelsLost = duelData[1]

            dbCursor.execute("SELECT roulettesWon, roulettesLost, slotsWon, slotsLost FROM gamblestats WHERE userId=%s", (uid,))
            gambleData = dbCursor.fetchone()
            roulettesWon = gambleData[0]
            roulettesLost = gambleData[1]
            slotsWon = gambleData[2]
            slotsLost = gambleData[3] 

            addressingMethod = "You" if targetUser == messageData.user else "They"

            bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} currently have {userPrimogems} primogems and have done {wishesDone} wishes so far. {addressingMethod} won {fiftyFiftiesWon} 50-50s and lost {fiftyFiftiesLost}. \
            {addressingMethod} own {len(owned5StarCharacters)} 5 star characters, {len(owned5StarWeapons)} 5 star weapons, {len(owned4StarCharacters)} 4 star characters \
            and {len(owned4StarWeapons)} 4 star weapons. {addressingMethod} have done {tradesDone} successful trades. {addressingMethod} won {duelsWon} duels and \
            lost {duelsLost} duels. Roulette W/L: {roulettesWon}/{roulettesLost} Slots W/L:{slotsWon}/{slotsLost} {self.proudEmote}")
        elif firstArg == "guarantee":
            targetUser = int(messageData.tags["user-id"])
            try:
                targetUser = args[2]
            except IndexError:
                pass

            userExists = None
            try:
                userExists = self.CheckUserRowExists(targetUser)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, {'you are not registered!' if targetUser == messageData.user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"]) if targetUser == messageData.user else self.GetTwitchUserID(targetUser)

            dbCursor.execute("SELECT has5StarGuaranteeOnCharacterBanner, has5StarGuaranteeOnWeaponBanner, has4StarGuaranteeOnCharacterBanner, has4StarGuaranteeOnWeaponBanner from wishstats where userId=%s", (uid,))
            result = dbCursor.fetchone()

            has5StarGuaranteeOnCharacterBanner = result[0]
            has5StarGuaranteeOnWeaponBanner = result[1]
            has4StarGuaranteeOnCharacterBanner = result[2]
            has4StarGuaranteeOnWeaponBanner = result[3]

            addressingMethod = "Your" if targetUser == messageData.user else "Their"

            positiveEmoji = "✅"
            negativeEmoji = "❌"
            bot.send_message(messageData.channel, f"{messageData.user}, {addressingMethod} current guarantee standings: Character banner 5 star {positiveEmoji if has5StarGuaranteeOnCharacterBanner else negativeEmoji} | \
            Character banner 4 star {positiveEmoji if has4StarGuaranteeOnCharacterBanner else negativeEmoji} | Weapon banner 5 star {positiveEmoji if has5StarGuaranteeOnWeaponBanner else negativeEmoji} | \
            Weapon banner 4 star {positiveEmoji if has4StarGuaranteeOnWeaponBanner else negativeEmoji}")
        elif firstArg == "help":
            bot.send_message(messageData.channel, f"{messageData.user}, {self.DESCRIPTION}")
        elif firstArg == "register":
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are already registered! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            self.CreateUserTableEntry(messageData.user, int(messageData.tags["user-id"]))

            bot.send_message(messageData.channel, f"{messageData.user}, you have been registered successfully! {self.proudEmote} You got {self.primogemAmountOnRegistration} primogems as a welcome bonus! {self.primogemEmote}")
        elif firstArg == "overview":
            dbCursor.execute("select SUM(wishesDone), SUM(fiftyFiftiesWon), SUM(fiftyFiftiesLost), COUNT(*) from wishstats;")
            result = dbCursor.fetchone()

            totalWishesDone = result[0]
            totalFiftyFiftiesWon = result[1]
            totalFiftyFiftiesLost = result[2]
            totalUserCount = result[3]

            bot.send_message(messageData.channel, f"{totalUserCount} users in the database have collectively done {totalWishesDone} wishes. {totalFiftyFiftiesWon} 50-50s were won \
            out of the total {totalFiftyFiftiesWon + totalFiftyFiftiesLost}. That's a {round((totalFiftyFiftiesWon / (totalFiftyFiftiesWon + totalFiftyFiftiesLost))*100, 2)}% win \
            rate! {self.neutralEmote}")
        elif firstArg == "duel":
            duelTarget = None
            duelAmount = None
            try:
                duelTarget = args[2]
                duelAmount = args[3]
            except IndexError:
                bot.send_message(messageData.channel, f"{messageData.user}, usage: _genshin duel (username) (amount). {self.thumbsUpEmote}")
                return self.CleanUpCommand(dbConnection)
            
            if duelTarget == botUsername:
                bot.send_message(messageData.channel, f"{messageData.user}, think you stand a chance against Paimon?! {self.stabEmote}")
                return self.CleanUpCommand(dbConnection)
            elif duelTarget == messageData.user:
                bot.send_message(messageData.channel, f"{messageData.user}, don't be so self-conflicted, love yourself! {self.thumbsUpEmote}")
                return self.CleanUpCommand(dbConnection)

            # See if these users are registered.
            isUserRegistered = None
            isTargetRegistered = None

            try:
                isUserRegistered = self.CheckUserRowExists(int(messageData.tags["user-id"]))
                isTargetRegistered = self.CheckUserRowExists(duelTarget)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not isUserRegistered:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            elif not isTargetRegistered:
                bot.send_message(messageData.channel, f"{messageData.user}, duel target {duelTarget} is not registered! Get them to use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")         
                return self.CleanUpCommand(dbConnection)

            # Get user and target Twitch UIDs.
            userUID = int(messageData.tags["user-id"])
            targetUID = self.GetTwitchUserID(duelTarget)
            
            # Get primogem and in-duel stats relating to both users.
            dbCursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelingWith, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
            userData = dbCursor.fetchone()
            userPrimogems = userData[0]
            userInDuel = userData[1]
            userDuelingWith = userData[2]
            userDuelStartTime = userData[3]

            dbCursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelingWith, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (targetUID,))
            targetData = dbCursor.fetchone()
            targetPrimogems = targetData[0]
            targetInDuel = targetData[1]
            targetDuelingWith = userData[2]
            targetDuelStartTime = userData[3]

            timeNow = datetime.datetime.now()

            try:
                duelAmount = int(duelAmount)
            except ValueError:
                # Parse the duel amount value.
                duelAmount = self.GetUserPrimogemsPartial(userPrimogems, duelAmount)

            if duelAmount == -1:
                bot.send_message(messageData.channel, f"{messageData.user}, couldn't parse the duel amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                return self.CleanUpCommand(dbConnection)

            # Do necessary checks before initiating the duel.
            if userInDuel:
                if int((timeNow - userDuelStartTime).total_seconds()) < self.duelTimeout:  # Since the functionality to timeout the duels would be too costly and unnecessary (and not because I'm lazy kappa), we just check the time differential.
                    bot.send_message(messageData.channel, f"{messageData.user}, you are already dueling with {userDuelingWith}! {self.angryEmote}")
                    return self.CleanUpCommand(dbConnection)
            elif targetInDuel:
                if int((timeNow - targetDuelStartTime).total_seconds()) < self.duelTimeout:
                    bot.send_message(messageData.channel, f"{messageData.user}, {duelTarget} is currently dueling with {targetDuelingWith}! {self.sadEmote}")
                    return self.CleanUpCommand(dbConnection)
            elif userPrimogems < duelAmount:
                bot.send_message(messageData.channel, f"{messageData.user}, you only have {userPrimogems} primogems! {self.shockedEmote}")
                return self.CleanUpCommand(dbConnection)
            elif targetPrimogems < duelAmount:
                bot.send_message(messageData.channel, f"{messageData.user}, {duelTarget} only has {targetPrimogems} primogems! {self.shockedEmote}")
                return self.CleanUpCommand(dbConnection)
            
            # No problems were found, the duel is on!

            # Update duelstats entries for both users.
            dbCursor.execute("UPDATE duelstats SET inDuel=TRUE, duelingWith=%s, duelAmount=%s, duelStartTime=NOW(), isInitiator=TRUE WHERE userId=%s", (duelTarget, duelAmount, userUID))
            dbConnection.commit()
            dbCursor.execute("UPDATE duelstats SET inDuel=TRUE, duelingWith=%s, duelAmount=%s, duelStartTime=NOW(), isInitiator=FALSE WHERE userId=%s", (messageData.user, duelAmount, targetUID))
            dbConnection.commit()

            # Announce the duel in the chat.
            bot.send_message(messageData.channel, f"{duelTarget}, {messageData.user} wants to duel you for {duelAmount} primogems! You can use _genshin duelaccept or _genshin dueldeny to respond within {self.duelTimeout} seconds! {self.stabEmote}")
        elif firstArg == "duelaccept":
            userUID = int(messageData.tags["user-id"])

            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))
            
            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            # See if the user is in a valid duel and get their primogem data.
            dbCursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelAmount, duelstats.duelingWith, duelstats.isInitiator, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
            userData = dbCursor.fetchone()
            userPrimogems = userData[0]
            inDuel = userData[1]
            duelAmount = userData[2]
            duelingWith = userData[3]
            isInitiator = userData[4]
            duelStartTime = userData[5]            
            
            timeNow = datetime.datetime.now()

            if inDuel:
                if int((timeNow - duelStartTime).total_seconds()) < self.duelTimeout:
                    # The duel is valid, we can continue.

                    # The duel initiator cannot accept the duel they started.
                    if isInitiator:
                        bot.send_message(messageData.channel, f"You can't accept the duel you started! You have to wait for {duelingWith} to accept the duel or wait until the timeout! {self.angryEmote}")
                        return self.CleanUpCommand(dbConnection)
                    
                    targetUID = None
                    try:
                        targetUID = self.GetTwitchUserID(duelingWith)
                    except:
                        bot.send_message(messageData.channel, f"{messageData.user}, cannot proceed due to a Twitch API error. Try again in a bit. {self.shockedEmote}")
                        return self.CleanUpCommand(dbConnection)

                    # Get opponent's primogem data.
                    dbCursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (targetUID,))
                    opponentPrimogems = dbCursor.fetchone()[0]

                    # See if both sides still have enough primogems. If not, cancel the duel.
                    if userPrimogems < duelAmount:
                        bot.send_message(messageData.channel, f"{messageData.user}, you don't have the same amount of primogems you had at the time of duel's start - the duel will be cancelled. {self.loserEmote}")

                        dbCursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                        dbConnection.commit()
                        return self.CleanUpCommand(dbConnection)
                    elif opponentPrimogems < duelAmount:
                        bot.send_message(messageData.channel, f"{messageData.user}, {duelingWith} doesn't have the same amount of primogems they had at the time of duel's start - the duel will be cancelled. {self.loserEmote}")
            
                        dbCursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                        dbConnection.commit()
                        return self.CleanUpCommand(dbConnection)
                    
                    # Duel begins!
                    duelists = [messageData.user, duelingWith]
                    winner = random.choice(duelists)
                    duelists.remove(winner)
                    loser = duelists[0]

                    winnerUID = userUID if winner == messageData.user else targetUID
                    loserUID = userUID if winner != messageData.user else targetUID

                    # Update primogems.
                    dbCursor.execute("UPDATE wishstats SET primogems = (CASE WHEN userId=%s THEN primogems+%s WHEN userId=%s THEN primogems-%s END) WHERE userID IN (%s, %s)", (winnerUID, duelAmount, loserUID, duelAmount, userUID, targetUID))
                    dbConnection.commit()

                    # Update duels won/lost stats.
                    dbCursor.execute("UPDATE duelstats SET duelsWon=duelsWon+1 WHERE userId=%s", (winnerUID,))
                    dbConnection.commit()
                    dbCursor.execute("UPDATE duelstats SET duelsLost=duelsLost+1 WHERE userId=%s", (loserUID,))
                    dbConnection.commit()

                    # These people are not in a duel anymore now that it's over, update this change in the database.
                    dbCursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                    dbConnection.commit()

                    # Announce the winner.
                    bot.send_message(messageData.channel, f"{winner} {self.danceEmote} won the duel against {loser} {self.loserEmote} for {duelAmount} primogems!")
                else:
                    bot.send_message(messageData.channel, f"{messageData.user}, you have no active duels to accept. {self.sadEmote}")
                    return self.CleanUpCommand(dbConnection)
            else:
                bot.send_message(messageData.channel, f"{messageData.user}, you have no active duels to accept. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

        elif firstArg == "dueldeny":
            userUID = int(messageData.tags["user-id"])
            
            userExists = self.CheckUserRowExists(messageData.user)
            
            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            # See if the user is in a valid duel and get their primogem data.
            dbCursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelAmount, duelstats.duelingWith, duelstats.isInitiator, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
            userData = dbCursor.fetchone()
            inDuel = userData[1]
            duelingWith = userData[3]
            isInitiator = userData[4]
            duelStartTime = userData[5]      
            
            timeNow = datetime.datetime.now()

            targetUID = None
            try:
                targetUID = self.GetTwitchUserID(duelingWith)
            except:
                bot.send_message(messageData.channel, f"Cannot proceed due to a Twitch API problem. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if inDuel:
                if int((timeNow - duelStartTime).total_seconds()) < self.duelTimeout and not isInitiator:
                    # Valid duel, move on with the denial.
                    dbCursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                    dbConnection.commit()

                    bot.send_message(messageData.channel, f"{duelingWith}, {messageData.user} denied your duel request. {self.shockedEmote}")
                else:
                    bot.send_message(messageData.channel, f"{messageData.user}, you have no active duels to deny! {self.angryEmote}")
                    return self.CleanUpCommand(dbConnection)
            else:
                bot.send_message(messageData.channel, f"{messageData.user}, you have no active duels to deny! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)
        
        elif firstArg in ["give", "giveprimos", "giveprimogems"]:            
            giveTarget = None
            giveAmount = None
            try:
                giveTarget = args[2]
                giveAmount = args[3]
            except IndexError:
                bot.send_message(messageData.channel, f"{messageData.user}, usage: _genshin {firstArg} (username) (amount). {self.thumbsUpEmote}")
                return self.CleanUpCommand(dbConnection)

            if giveTarget == messageData.user:
                bot.send_message(messageData.channel, f"{messageData.user}, you gave yourself your own {giveAmount} primogems and you now have exactly the same amount. Paimon approves! {self.thumbsUpEmote}")
                return self.CleanUpCommand(dbConnection)
            elif giveTarget == botUsername:
                bot.send_message(messageData.channel, f"{messageData.user}, Paimon appreciates the gesture, but she'd prefer if you kept your points. {self.shyEmote}")
                return self.CleanUpCommand(dbConnection)
            
            # See if these users are registered.
            isUserRegistered = None
            isTargetRegistered = None

            try:
                isUserRegistered = self.CheckUserRowExists(int(messageData.tags["user-id"]))
                isTargetRegistered = self.CheckUserRowExists(giveTarget)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            if not isUserRegistered:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            elif not isTargetRegistered:
                bot.send_message(messageData.channel, f"{messageData.user}, target {giveTarget} is not registered! Get them to use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")         
                return self.CleanUpCommand(dbConnection)

            userUID = int(messageData.tags["user-id"])
            targetUID = None
            try:
                targetUID = self.GetTwitchUserID(giveTarget)
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, cannot proceed due to a Twitch API error. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            # See if the user has enough primogems.
            dbCursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (userUID,))
            userPrimogems = dbCursor.fetchone()[0]

            try:
                giveAmount = int(giveAmount)
            except ValueError:
                giveAmount = self.GetUserPrimogemsPartial(userPrimogems, giveAmount)

            if giveAmount == -1:
                bot.send_message(messageData.channel, f"{messageData.user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                return self.CleanUpCommand(dbConnection)

            # Reject invalid amounts.
            if giveAmount <= 0:
                bot.send_message(messageData.channel, f"{messageData.user}, Paimon thinks {giveTarget} would appreciate it more if you gave them a positive amount of primogems! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            if userPrimogems < giveAmount:
                bot.send_message(messageData.channel, f"{messageData.user}, you only have {userPrimogems} primogems! {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)
            
            # Update primogems.
            dbCursor.execute("UPDATE wishstats SET primogems = (CASE WHEN userId=%s THEN primogems+%s WHEN userId=%s THEN primogems-%s END) WHERE userId IN (%s, %s)", (targetUID, giveAmount, userUID, giveAmount, userUID, targetUID))
            dbConnection.commit()

            # Announce the successful exchange.
            bot.send_message(messageData.channel, f"{messageData.user} gave {giveAmount} primogems to {giveTarget}! {self.shyEmote}")
            
        elif firstArg in ["banner", "banners"]:
            message = ""

            currentIndex = 0

            for banner in self.pulledBannerData:
                # Add the names of all the 5 stars if it isn't the standard banner.
                if banner["gacha_type"] != 200:
                    rateUp5Stars = []
                    internalBannerName = ""

                    if banner["gacha_type"] == 301:
                        internalBannerName = "character1"
                    elif banner["gacha_type"] == 400:
                        internalBannerName = "character2"
                    elif banner["gacha_type"] == 302:
                        internalBannerName = "weapon"

                    for item in banner["r5_up_items"]:
                        rateUp5Stars.append(item["item_name"])

                    HTMLTagStrippedBannerName = re.sub("<[^>]*>", "", banner["title"])

                    message += f"({internalBannerName})" + " " + HTMLTagStrippedBannerName + ": " + ", ".join(rateUp5Stars) + "✨ "
                else:
                    internalStandardBannerName = "standard"

                    HTMLTagStrippedBannerName = re.sub("<[^>]*>", "", banner["title"])

                    message += f"({internalStandardBannerName})" + " " + HTMLTagStrippedBannerName + "✨ "

                currentIndex += 1

            bot.send_message(messageData.channel, f"{messageData.user}, Current banners are: {message}")

        elif firstArg == "update":
            if messageData.user != AUTHORIZED_USER:
                bot.send_message(messageData.channel, "🤨")
                return self.CleanUpCommand(dbConnection)
            
            self.UpdateBannerData()
            bot.send_message(messageData.channel, f"Successfully updated the wish schedule. Current banner names are: {', '.join(self.validBannerNames)}")

        elif firstArg in ["gamble", "roulette"]:
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"])

            dbCursor.execute("SELECT primogems FROM wishstats where userId=%s", (uid,))

            result = dbCursor.fetchone()
            ownedPrimogems = result[0]

            betAmount = 0
            try:
                betAmount = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"{messageData.user}, you haven't entered an amount to bet! Example usage: _genshin roulette all {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            
            try:
                betAmount = int(betAmount)
            except ValueError:
                # Parse the bet amount value if it can't be parsed to an int.
                betAmount = self.GetUserPrimogemsPartial(ownedPrimogems, betAmount)

            if betAmount == -1:
                bot.send_message(messageData.channel, f"{messageData.user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                return self.CleanUpCommand(dbConnection)
            
            if betAmount < 0:
                bot.send_message(messageData.channel, f"{messageData.user}, no loans! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            if betAmount < self.rouletteMinBet:
                bot.send_message(messageData.channel, f"{messageData.user}, minimum bet for roulette is {self.rouletteMinBet} primogems. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            # Check if user has enough primogems.
            if ownedPrimogems < betAmount:
                bot.send_message(messageData.channel, f"{messageData.user}, you wanted to bet {betAmount} primogems, but you only have {ownedPrimogems} primogems! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            # Now check if user won the roulette.
            randomValue = random.randint(0, 100)
            if randomValue < self.rouletteWinChancePercentage:
                # User has won the roulette, give them their primogems.
                earnedPrimogems = betAmount * self.rouletteWinMultiplier

                dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (earnedPrimogems, uid))
                dbCursor.execute("UPDATE gamblestats SET roulettesWon=roulettesWon+1 WHERE userId=%s", (uid,))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user} has won {earnedPrimogems} primogems in roulette, and they now have {earnedPrimogems + ownedPrimogems} primogems! {self.primogemEmote}")
            else:
                # User has lost the roulette, take their loss from them.
                lostPrimogems = betAmount

                dbCursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (lostPrimogems, uid))
                dbCursor.execute("UPDATE gamblestats SET roulettesLost=roulettesLost+1 WHERE userId=%s", (uid,))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user} has lost {lostPrimogems} primogems in roulette, and they now have {ownedPrimogems - lostPrimogems} primogems! {self.shockedEmote}")
        
        elif firstArg in ["slot", "slots"]:
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"])

            dbCursor.execute("SELECT primogems FROM wishstats where userId=%s", (uid,))

            result = dbCursor.fetchone()
            ownedPrimogems = result[0]

            betAmount = 0
            try:
                betAmount = args[2]
            except IndexError:
                bot.send_message(messageData.channel, f"{messageData.user}, you haven't entered an amount to bet! Example usage: _genshin slots all {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)
            
            try:
                betAmount = int(betAmount)
            except ValueError:
                # Parse the bet amount value if it can't be parsed to an int.
                betAmount = self.GetUserPrimogemsPartial(ownedPrimogems, betAmount)

            if betAmount == -1:
                bot.send_message(messageData.channel, f"{messageData.user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                return self.CleanUpCommand(dbConnection)

            if betAmount < 0:
                bot.send_message(messageData.channel, f"{messageData.user}, no loans! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            if betAmount < self.slotsMinBet:
                bot.send_message(messageData.channel, f"{messageData.user}, minimum bet for slots is {self.slotsMinBet} primogems. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

            # Check if user has enough primogems.
            if ownedPrimogems < betAmount:
                bot.send_message(messageData.channel, f"{messageData.user}, you wanted to bet {betAmount} primogems, but you only have {ownedPrimogems} primogems! {self.angryEmote}")
                return self.CleanUpCommand(dbConnection)

            # Now, do the slot rolls!
            firstElement = random.choice(self.slotsElements)
            secondElement = random.choice(self.slotsElements)
            thirdElement = random.choice(self.slotsElements)

            slotsResult = f"{firstElement} | {secondElement} | {thirdElement}"

            # Check for slots win.
            if firstElement == secondElement == thirdElement:
                earnedPrimogems = betAmount * self.slotsWinMultiplier

                dbCursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (earnedPrimogems, uid))
                dbCursor.execute("UPDATE gamblestats SET slotsWon=slotsWon+1 WHERE userId=%s", (uid,))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user} you got {slotsResult} in slots and won {earnedPrimogems} primogems!!! You now have {ownedPrimogems + earnedPrimogems} primogems!!! {self.primogemEmote} {self.primogemEmote} {self.primogemEmote}")
            else:
                # User has lost the roulette, take their loss from them.
                lostPrimogems = betAmount

                dbCursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (lostPrimogems, uid))
                dbCursor.execute("UPDATE gamblestats SET slotsLost=slotsLost+1 WHERE userId=%s", (uid,))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user} you got {slotsResult} in slots and lost {lostPrimogems} primogems. You now have {ownedPrimogems - lostPrimogems} primogems. {self.sadEmote}")
        
        elif firstArg in "updatename":
            userExists = self.CheckUserRowExists(int(messageData.tags["user-id"]))

            if not userExists:
                bot.send_message(messageData.channel, f"{messageData.user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                return self.CleanUpCommand(dbConnection)

            uid = int(messageData.tags["user-id"])

            try:
                userData = requests.get(f"https://api.twitch.tv/helix/channels?broadcaster_id={uid}", headers=TWITCH_API_HEADERS)
                newUsername = userData.json()["data"][0]["broadcaster_name"]

                dbCursor.execute("UPDATE wishstats SET username=%s where userId=%s", (newUsername, uid))
                dbCursor.execute("UPDATE duelstats SET username=%s where userId=%s", (newUsername, uid))
                dbCursor.execute("UPDATE tradestats SET username=%s where userId=%s", (newUsername, uid))
                dbCursor.execute("UPDATE gamblestats SET username=%s where userId=%s", (newUsername, uid))
                dbConnection.commit()

                bot.send_message(messageData.channel, f"{messageData.user}, Successfully updated your new name in the database! {self.proudEmote}")
            except:
                bot.send_message(messageData.channel, f"{messageData.user}, An error occured while updating name. {self.sadEmote}")
                return self.CleanUpCommand(dbConnection)

        dbConnection.close()