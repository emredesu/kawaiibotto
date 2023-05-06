from commands.command import Command
from messagetypes import error, log
from globals import TWITCH_API_HEADERS, USERNAME as botUsername, GENSHIN_MYSQL_DB_HOST, GENSHIN_MYSQL_DB_USERNAME, GENSHIN_MYSQL_DB_PASSWORD, AUTHORIZED_USER
import random
import requests
import mysql.connector
import traceback
import datetime
import json
import re
from threading import Lock

class GenshinCommand(Command):
    COMMAND_NAME = ["genshin", "genshit"]
    COOLDOWN = 0
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

    bannerInfoGistLink = "https://gist.githubusercontent.com/emredesu/2766beb7e57c55b5d0cee9294f96cfa1/raw/kawaiibottoGenshinWishBanners.json"
    emojiAssociationGistLink = "https://gist.githubusercontent.com/emredesu/e13a6274d9ba9825562b279d00bb1c0b/raw/kawaiibottoGenshinEmojiAssociations.json"
    bannerImagesGistLink = "https://gist.githubusercontent.com/emredesu/9afb788b25c155ce2c6c53170a02d955/raw/kawaiibottoBannerImageLinks.json"

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

    characterBanner5StarRateUpProbability = 50
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

    # Bot emotes. These are all 7tv emotes!
    sadEmote = "PaimonSad"
    danceEmote = "PaimonDance"
    loserEmote = "PaimonBlehh"
    shockedEmote = "PaimonShocked"
    tantrumEmote = "paimonTantrum"
    angryEmote = "paimonEHE"
    primogemEmote = "paimonWhale"
    proudEmote = "paimonHeh"
    deadEmote = "QiqiSleep"
    neutralEmote = "HungryPaimon"
    shyEmote = "paimonShy"
    ayayaEmote = "paimonAYAYA"
    derpEmote = "paimonDerp"
    nomEmote = "paimonCookie"
    emergencyFoodEmote = "paimonEmergencyFood"
    thumbsUpEmote = "paimonThumbsUp"
    stabEmote = "paimonStab"

    # Roulette values
    rouletteWinChancePercentage = 45
    rouletteWinMultiplier = 1

    # Slots values
    slotsElements = [neutralEmote, danceEmote, loserEmote, tantrumEmote, primogemEmote, proudEmote, ayayaEmote, derpEmote, nomEmote, stabEmote]
    slotsWinMultiplier = 10

    mutex = Lock()

    def __init__(self, commands):
        super().__init__(commands)
        self.UpdateFromGist()

        try:
            self.database = mysql.connector.connect(host=GENSHIN_MYSQL_DB_HOST, user=GENSHIN_MYSQL_DB_USERNAME, password=GENSHIN_MYSQL_DB_PASSWORD, database="genshinStats")
            self.cursor = self.database.cursor()
        except Exception as e:
            error(f"Fatal error while connecting to the database: {e.__class__.__name__}")
            traceback.print_exc()
            self.successfulInit = False

    def UpdateFromGist(self):
        try:
            jsonData = requests.get(self.bannerInfoGistLink).json()
            self.bannerData = jsonData
            self.bannerImageLinks = requests.get(self.bannerImagesGistLink).json()

            self.validBannerNames.clear()

            for bannerName in jsonData:
                self.validBannerNames.append(bannerName)

            self.emojiAssociations = requests.get(self.emojiAssociationGistLink).json()
        except Exception as e:
            error(f"Fatal error while getting gist data for the Genshin command: {e.__class__.__name__}")
            self.successfulInit = False

    def GetTwitchUserID(self, username) -> int: 
        url = f"https://api.twitch.tv/helix/users?login={username}"

        data = requests.get(url, headers=TWITCH_API_HEADERS).json()

        try:
            userid = data["data"][0]["id"]
            return int(userid)
        except IndexError:
            return -1

    def CheckUserRowExists(self, username) -> bool:
        uid = self.GetTwitchUserID(username)
        if uid == -1:
            return False

        self.cursor.execute("SELECT * from wishstats where userId=%s", (uid,))

        result = self.cursor.fetchone()

        return False if result is None else True

    def CreateUserTableEntry(self, username):
        uid = self.GetTwitchUserID(username)

        # Register on wishstats table
        # Subtracting two hours from the current time to allow the user to wish after getting registered. Give the user {self.primogemAmountOnRegistration} primogems on registration.
        self.cursor.execute("INSERT INTO wishstats VALUES (%s, %s, %s, 0, SUBTIME(NOW(), \"2:0:0\"), 0, 0, 0, 0, 0, FALSE, FALSE, FALSE, FALSE, \"{}\", \"{}\", \"{}\", \"{}\", 0, 0, 0)", (username, uid, self.primogemAmountOnRegistration))
        self.database.commit()

        # Register on duelstats table
        self.cursor.execute("INSERT INTO duelstats VALUES (%s, %s, FALSE, 0, %s, FALSE, 0, 0, SUBTIME(NOW(), 1800))", (username, uid, "nobodyxd")) # dummy values
        self.database.commit()

        # Register on the tradestats table
        self.cursor.execute("INSERT INTO tradestats VALUES (%s, %s, FALSE, FALSE, FALSE, %s, %s, %s, %s, 0, SUBTIME(NOW(), 1800), 0)", (username, uid, "nothingxd", "nostar",
                                                                                                                                     "noqual", "nobodyxd")) # dummy values

        self.cursor.execute("INSERT INTO gamblestats VALUES (%s, %s, 0, 0, 0, 0)", (username, uid))

        self.database.commit()

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

    def execute(self, bot, user, message, channel):
        if not self.successfulInit:
            bot.send_message(channel, f"This command has not been initialized properly... sorry! {self.emergencyFoodEmote}")
            return

        args = message.split()

        with self.mutex:
            validFirstArgs = ["claim", "redeem", "wish", "characters", "weapons", "top", "register", "pity", "pitycheck", "pitycounter", "stats", "guarantee", "help", 
            "overview", "duel", "duelaccept", "dueldeny", "give", "giveprimos", "giveprimogems", "trade", "tradeaccept", "tradedeny", "primogems", "primos", "points",
            "banner", "banners", "update", "gamble", "roulette", "slots", "updatename"]

            firstArg = None
            try:
                firstArg = args[1]
            except IndexError:
                bot.send_message(channel, f"{user}, {self.DESCRIPTION}")
                return

            if firstArg not in validFirstArgs:
                bot.send_message(channel, f"Invalid first argument supplied! Valid first arguments are: {' '.join(validFirstArgs)}")
                return
        
            if firstArg in ["claim", "redeem"]:
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error.")
                    return

                self.cursor.execute("SELECT primogems, lastRedeemTime FROM wishstats where userId=%s", (uid,))

                result = self.cursor.fetchone()
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
                    
                    self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s, lastRedeemTime=NOW() WHERE userId=%s", (claimAmount, uid))
                    self.database.commit()

                    bot.send_message(channel, f"{user}, you have successfully claimed {claimAmount} primogems! \
                    You now have {ownedPrimogems + claimAmount} primogems! {self.primogemEmote}")
                else:
                    timeUntilClaim = str(datetime.timedelta(seconds=self.requiredSecondsBetweenRedeems-int(timePassed.total_seconds())))
                    bot.send_message(channel, f"{user}, you can't claim primogems yet - your next claim will be available in: {timeUntilClaim} {self.sadEmote}")
                    return

            elif firstArg == "wish":
                validSecondArgs = self.validBannerNames
                
                try:
                    secondArg = args[2]
                except IndexError:
                    bot.send_message(channel, f"Please provide a banner name to wish on. Current banner names are: {' '.join(validSecondArgs)}")
                    return

                if secondArg not in validSecondArgs:
                    bot.send_message(channel, f"Please provide a valid banner name. Current valid banner names are: {' '.join(validSecondArgs)} | Example usage: _genshin wish {random.choice(validSecondArgs)}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                wishCount = 1
                try:
                    wishCount = int(args[3]) # See if the user has supplied a third argument as how many wishes they want to make.
                    if wishCount < 1:
                        bot.send_message(channel, f"{user}, don't mess with Paimon! You can't do {wishCount} wishes! {self.angryEmote}")
                        return
                    elif wishCount > 10:
                        bot.send_message(channel, f"{user}, you can't do more than 10 wishes at once! {self.angryEmote}")
                        return
                except IndexError:
                    pass
                except (ValueError, SyntaxError):
                    bot.send_message(channel, f"{user}, \"{args[3]}\" is not an integer! {self.tantrumEmote} Example usage: _genshin wish {random.choice(validSecondArgs)} {random.randint(1, 10)}")
                    return

                isMultiWish = False if wishCount == 1 else True

                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error! {self.tantrumEmote}")
                    return

                self.cursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (uid,))
                ownedPrimogems = self.cursor.fetchone()[0]

                primogemCost = self.wishCost * wishCount

                if ownedPrimogems >= primogemCost:
                    # Deduct primogems.
                    self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (primogemCost, uid,))
                    self.database.commit()

                    targetString = ""

                    # ----- Character banner -----
                    if "character" in secondArg:
                        for i in range(wishCount):
                            self.cursor.execute(f"SELECT characterBannerPityCounter, wishesSinceLast4StarOnCharacterBanner FROM wishstats where userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
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
                                self.cursor.execute("SELECT owned5StarCharacters, has5StarGuaranteeOnCharacterBanner FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = self.cursor.fetchone()

                                characterData = json.loads(retrievedData[0])
                                hasGuarantee = retrievedData[1]

                                rateUpWeaponRoll = random.uniform(0, 100)
                                if rateUpWeaponRoll < self.characterBanner5StarRateUpProbability or hasGuarantee:
                                    # We got the banner character!
                                    acquiredCharacter = self.bannerData[secondArg]["rateUp5StarCharacter"]
                                    
                                    if not isMultiWish:
                                        targetString = f"{user}, you beat the 50-50" if not hasGuarantee else f"{user}, you used up your guarantee"
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
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()
                                            
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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=false, characterBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData) ,uid))
                                    self.database.commit()

                                    # 50-50 win/lose counting
                                    if not hasGuarantee:
                                        self.cursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                        self.database.commit()

                                else:
                                    # We lost the 5 star 50-50 :/
                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you lost your 50-50 and got {acquiredCharacter}(5🌟){self.GetEmojiAssociation(acquiredCharacter)}! {self.shockedEmote}"
                                    else:
                                        targetString += f"| {acquiredCharacter}(5🌟)"

                                    if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give primogems to the user.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=true, characterBannerPityCounter=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (json.dumps(characterData), uid))
                                    self.database.commit()

                            elif userGotA4Star:
                                # We got a 4 star!

                                # Increment the pity counter.
                                self.cursor.execute("UPDATE wishstats SET characterBannerPityCounter=characterBannerPityCounter+1 WHERE userId=%s", (uid,))
                                self.database.commit()

                                # Get user info related to 4 stars.
                                self.cursor.execute("SELECT has4StarGuaranteeOnCharacterBanner, owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = self.cursor.fetchone()
                                hasGuarantee = retrievedData[0]
                                characterData = json.loads(retrievedData[1])

                                rateUpWeaponRoll = random.uniform(0, 100)
                                if rateUpWeaponRoll < self.characterBanner4StarRateUpProbability or hasGuarantee:
                                    # We won the 4 star 50-50!

                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["rateUp4StarCharacters"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you won the 50-50" if not hasGuarantee else f"{user}, you used up your 4 star guarantee"
                                        targetString += f" and got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}!"
                                    else:
                                        targetString += f"| {acquiredCharacter}(4⭐)"

                                    if acquiredCharacter not in characterData:
                                        characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give primogems to the user.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, has4StarGuaranteeOnCharacterBanner=false, wishesSinceLast4StarOnCharacterBanner=0 WHERE userId=%s",
                                    (json.dumps(characterData), uid))
                                    self.database.commit()

                                    # 50-50 win/lose counting
                                    if not hasGuarantee:
                                        self.cursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                        self.database.commit()

                                else:
                                    # We lost the 4 star 50-50 :/

                                    acquiredItem = random.choice(["weapon", "character"])
                                    if acquiredItem == "weapon":
                                        acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                        if not isMultiWish:
                                            targetString += f"{user}, you lost the 4 star 50-50 and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.shockedEmote}"
                                        else:
                                            targetString += f"| {acquiredWeapon}(4⭐)"

                                        self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                        weaponData = json.loads(self.cursor.fetchone()[0])

                                        if acquiredWeapon not in weaponData:
                                            weaponData[acquiredWeapon] = "R1"
                                        else:
                                            # Give user primogems if the weapon is already maxed out.
                                            if weaponData[acquiredWeapon] == "R5":
                                                # Give user primogems.
                                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                                self.database.commit()

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
                                        self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                        self.database.commit()

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
                                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                                self.database.commit()

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
                                        self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                        self.database.commit()

                                    # Finally, update the database data to have pity for the next 4 star.
                                    self.cursor.execute("UPDATE wishstats SET has4StarGuaranteeOnCharacterBanner=true, wishesSinceLast4StarOnCharacterBanner=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (uid,))
                                    self.database.commit()
                                
                            else:
                                acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                                # Increment the pity counters for 4 star and 5 star.
                                self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnCharacterBanner=wishesSinceLast4StarOnCharacterBanner+1, characterBannerPityCounter=characterBannerPityCounter+1 WHERE userId=%s", (uid,))

                                if not isMultiWish:
                                    targetString += f"{user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                                else:
                                    targetString += f"| {acquiredTrash}(3★) "

                    # ----- Standard banner -----                    
                    elif "standard" in secondArg:
                        for i in range(wishCount):
                            self.cursor.execute("SELECT standardBannerPityCounter, wishesSinceLast4StarOnStandardBanner FROM wishstats where userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
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
                                    self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                                    retrievedData = self.cursor.fetchone()
                                    characterData = json.loads(retrievedData[0])

                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you got {acquiredCharacter}(5🌟){self.GetEmojiAssociation(acquiredCharacter)}! {self.neutralEmote}"
                                    else:
                                        targetString += f"| {acquiredCharacter}(5🌟)"

                                    if acquiredCharacter not in characterData:
                                            characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData), uid,))
                                    self.database.commit()
                                else:
                                    # Get info related to owned 5 star weapons.
                                    self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                    retrievedData = self.cursor.fetchone()
                                    weaponData = json.loads(retrievedData[0])

                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}! {self.neutralEmote}"
                                    else:
                                        targetString += f"| {acquiredWeapon}(5🌟)"

                                    if acquiredWeapon not in weaponData:
                                            weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give out primogems if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                    self.database.commit()
                    
                            elif userGotA4Star:
                                # We got a 4 star.

                                # Increment the pity counter.
                                self.cursor.execute("UPDATE wishstats SET standardBannerPityCounter=standardBannerPityCounter+1 WHERE userId=%s", (uid,))
                                self.database.commit()

                                isCharacter = True if random.choice([0, 1]) == 0 else False
                                if isCharacter:
                                    # Get info related to owned 4 star characters.
                                    self.cursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                                    retrievedData = self.cursor.fetchone()
                                    characterData = json.loads(retrievedData[0])

                                    acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you got {acquiredCharacter}(4⭐){self.GetEmojiAssociation(acquiredCharacter)}! {self.neutralEmote}"
                                    else:
                                        targetString += f"| {acquiredCharacter}(4⭐)"

                                    if acquiredCharacter not in characterData:
                                            characterData[acquiredCharacter] = "C0"
                                    else:
                                        if characterData[acquiredCharacter] == "C6":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(characterData), uid))
                                    self.database.commit()
                                else:
                                    # Get info related to owned 4 star weapons.
                                    self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                    retrievedData = self.cursor.fetchone()
                                    weaponData = json.loads(retrievedData[0])

                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.neutralEmote}"
                                    else:
                                        targetString += f"| {acquiredWeapon}(4⭐)"

                                    if acquiredWeapon not in weaponData:
                                            weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Reset wish timer if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                    self.database.commit()
                            else:
                                acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                                # Increment the pity counters for 5 star and 4 star.
                                self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnStandardBanner=wishesSinceLast4StarOnStandardBanner+1, standardBannerPityCounter=standardBannerPityCounter+1 WHERE userId=%s", (uid,))

                                if not isMultiWish:
                                    targetString += f"{user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                                else:
                                    targetString += f"| {acquiredTrash}(3★) "

                    # ----- Weapon banner -----
                    else:
                        for i in range(wishCount):
                            # Get data regarding the weapon banner.
                            self.cursor.execute("SELECT weaponBannerPityCounter, has5StarGuaranteeOnWeaponBanner, has4StarGuaranteeOnWeaponBanner, wishesSinceLast4StarOnWeaponBanner from wishstats WHERE userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
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
                                self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                weaponData = json.loads(self.cursor.fetchone()[0])

                                # Roll a random chance or see if we have guarantee to check if the 5 star we got is one of the featured ones.
                                if random.uniform(0, 100) < self.weaponBanner5StarRateUpProbability or hasGuarantee5Star:
                                    # We got one of the featured weapons!
                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["rateUp5StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you beat the odds of 75-25" if not hasGuarantee5Star else f"{user}, you used up your guarantee"
                                        targetString += f" and got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}!"
                                    else:
                                        targetString += f"| {acquiredWeapon}(5🌟)"

                                    if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give the user primogems if the weapon was already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=false, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                    self.database.commit()
                                else:
                                    # We lost the 75-25.
                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{user}, You lost the 75-25 and got {acquiredWeapon}(5🌟){self.GetEmojiAssociation(acquiredWeapon)}! {self.shockedEmote}"
                                    else:
                                        targetString += f"| {acquiredWeapon}(5🌟)"

                                    if acquiredWeapon not in weaponData:
                                        weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give the user primogems if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=true, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid,))
                                    self.database.commit()

                            elif userGotA4Star:
                                # We got a 4 star.

                                # Increment the pity counter.
                                self.cursor.execute("UPDATE wishstats SET weaponBannerPityCounter=weaponBannerPityCounter+1 WHERE userId=%s", (uid,))
                                self.database.commit()
                                
                                # Get user info related to 4 stars.
                                self.cursor.execute("SELECT has4StarGuaranteeOnWeaponBanner, owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                retrievedData = self.cursor.fetchone()
                                hasGuarantee = retrievedData[0]
                                weaponData = json.loads(retrievedData[1])

                                rateUpWeaponRoll = random.uniform(0, 100)
                                if rateUpWeaponRoll < self.weaponBanner4StarRateUpProbability or hasGuarantee4Star:
                                    # We won the 4 star 50-50!

                                    acquiredWeapon = random.choice(self.bannerData[secondArg]["rateUp4StarWeapons"])

                                    if not isMultiWish:
                                        targetString = f"{user}, you won the 50-50" if not hasGuarantee else f"{user}, you used up your 4 star guarantee"
                                        targetString += f" and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}!"
                                    else:
                                        targetString += f"| {acquiredWeapon}(4⭐)"

                                    if acquiredWeapon not in weaponData:
                                            weaponData[acquiredWeapon] = "R1"
                                    else:
                                        # Give the user primogems if the weapon is already maxed out.
                                        if weaponData[acquiredWeapon] == "R5":
                                            # Give user primogems.
                                            self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                            self.database.commit()

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
                                    self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, has4StarGuaranteeOnWeaponBanner=false, wishesSinceLast4StarOnWeaponBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                                    self.database.commit()
                                else:
                                    # We lost the 4 star 50-50 :/

                                    acquiredItem = random.choice(["weapon", "character"])
                                    if acquiredItem == "weapon":
                                        acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                        if not isMultiWish:
                                            targetString = f"{user}, you lost the 4 star 50-50"
                                            targetString += f" and got {acquiredWeapon}(4⭐){self.GetEmojiAssociation(acquiredWeapon)}! {self.sadEmote}"
                                        else:
                                            targetString += f"| {acquiredWeapon}(4⭐)"

                                        self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                        weaponData = json.loads(self.cursor.fetchone()[0])

                                        if acquiredWeapon not in weaponData:
                                            weaponData[acquiredWeapon] = "R1"
                                        else:
                                            # Give the user primogems if the weapon is already maxed out.
                                            if weaponData[acquiredWeapon] == "R5":
                                                # Give user primogems.
                                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                                self.database.commit()

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
                                        self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                        self.database.commit()
                                    else:
                                        self.cursor.execute("SELECT owned4StarCharacters from wishstats WHERE userId=%s", (uid,))
                                        characterData = json.loads(self.cursor.fetchone()[0])

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
                                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (self.primogemAmountOnRedeem, uid))
                                                self.database.commit()

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
                                        self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                        self.database.commit()

                                    # Finally, update the database data to have pity for the next 4 star.
                                    self.cursor.execute("UPDATE wishstats SET has4StarGuaranteeOnWeaponBanner=true, wishesSinceLast4StarOnWeaponBanner=0 WHERE userId=%s", (uid,))
                                    self.database.commit()                        
                            else:
                                acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                                # Increment the pity counters for 4 star and 5 star.
                                self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnWeaponBanner=wishesSinceLast4StarOnWeaponBanner+1, weaponBannerPityCounter=weaponBannerPityCounter+1 WHERE userId=%s", (uid,))

                                if not isMultiWish:
                                    targetString += f"{user}, you got a {acquiredTrash}(3★) {self.nomEmote}"
                                else:
                                    targetString += f"| {acquiredTrash}(3★) "
                else:
                    bot.send_message(channel, f"{user}, you need {primogemCost} primogems for that, but you have {ownedPrimogems}! {self.primogemEmote}")
                    return

                # Increase the user's wish counter.
                self.cursor.execute("UPDATE wishstats SET wishesDone=wishesDone+%s WHERE userId=%s", (wishCount, uid))
                self.database.commit()

                bot.send_message(channel, (user + ", " if isMultiWish else "") + targetString)
            elif firstArg == "characters":
                validSecondArgs = ["4star", "5star"]
                secondArg = None

                targetUser = user

                try:
                    secondArg = args[2]
                except IndexError:
                    bot.send_message(channel, f"Please provide a character type to retrieve. Character types are: {' '.join(validSecondArgs)}")
                    return
                
                try:
                    targetUser = args[3]
                except IndexError:
                    pass

                targetUser = targetUser.strip("@,")

                addressingMethod = "you" if targetUser == user else "they"

                if secondArg not in validSecondArgs:
                    bot.send_message(channel, f"Please provide a valid character type. Valid character types are: {' '.join(validSecondArgs)} | Example usage: _genshin characters {random.choice(validSecondArgs)}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, {addressingMethod} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return
                else:
                    uid = None
                    try:
                        uid = self.GetTwitchUserID(targetUser)
                    except:
                        bot.send_message(channel, f"{user}, unable to show characters due to a Twitch API error! {self.tantrumEmote}")
                        return

                    if secondArg == "5star":
                        self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                        characterData = json.loads(self.cursor.fetchone()[0])

                        if len(characterData.items()) == 0:
                            bot.send_message(channel, f"{user}, {addressingMethod} have no 5 star characters to show. {self.deadEmote}")
                            return

                        targetString = ""

                        currentLoopCount = 0
                        for key, pair in characterData.items():
                            currentLoopCount += 1

                            targetString += f"{key} ({pair})"
                            
                            if currentLoopCount < len(characterData.items()):
                                targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                        
                        bot.send_message(channel, f"{user}, {targetString}")
                    else:
                        self.cursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                        characterData = json.loads(self.cursor.fetchone()[0])

                        if len(characterData.items()) == 0:
                            bot.send_message(channel, f"{user}, {addressingMethod} have no 4 star characters to show. {self.deadEmote}")
                            return

                        targetString = ""

                        currentLoopCount = 0
                        for key, pair in characterData.items():
                            currentLoopCount += 1

                            targetString += f"{key} ({pair})"
                            
                            if currentLoopCount < len(characterData.items()):
                                targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                        
                        bot.send_message(channel, f"{user}, {targetString}")
            elif firstArg == "weapons":
                validSecondArgs = ["4star", "5star"]
                secondArg = None

                targetUser = user

                try:
                    secondArg = args[2]
                except IndexError:
                    bot.send_message(channel, f"Please provide a weapon type to retrieve. Valid weapon types are: {' '.join(validSecondArgs)}")
                    return
                
                try:
                    targetUser = args[3]
                except IndexError:
                    pass

                targetUser = targetUser.strip("@,")

                addressingMethod = "you" if targetUser == user else "they"

                if secondArg not in validSecondArgs:
                    bot.send_message(channel, f"Please provide a valid weapon type. Valid weapon types are: {' '.join(validSecondArgs)} | Example usage: _genshin weapons {random.choice(validSecondArgs)}")
                    return

                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return
            
                if not userExists:
                    bot.send_message(channel, f"{user}, {addressingMethod} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return
                else:
                    uid = None
                    try:
                        uid = self.GetTwitchUserID(targetUser)
                    except:
                        bot.send_message(channel, f"{user}, unable to show weapons due to a Twitch API error! {self.tantrumEmote}")
                        return

                    if secondArg == "5star":
                        self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                        weaponData = json.loads(self.cursor.fetchone()[0])

                        if len(weaponData.items()) == 0:
                            bot.send_message(channel, f"{user}, {addressingMethod} have no 5 star weapons to show. {self.deadEmote}")
                            return

                        targetString = ""

                        currentLoopCount = 0
                        for key, pair in weaponData.items():
                            currentLoopCount += 1

                            targetString += f"{key} ({pair})"
                            
                            if currentLoopCount < len(weaponData.items()):
                                targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                        
                        bot.send_message(channel, f"{user}, {targetString}")
                    else:
                        self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                        weaponData = json.loads(self.cursor.fetchone()[0])

                        if len(weaponData.items()) == 0:
                            bot.send_message(channel, f"{user}, {addressingMethod} have no 4 star weapons to show. {self.deadEmote}")
                            return

                        targetString = ""

                        currentLoopCount = 0
                        for key, pair in weaponData.items():
                            currentLoopCount += 1

                            targetString += f"{key} ({pair})"
                            
                            if currentLoopCount < len(weaponData.items()):
                                targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                        
                        bot.send_message(channel, f"{user}, {targetString}")
            elif firstArg in ["primogems", "primos", "points"]:
                targetUser = user
                try:
                    targetUser = args[2]
                except IndexError:
                    pass

                targetUser = targetUser.strip("@,")

                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, {'you are not registered!' if targetUser == user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show primogems due to a Twitch API error! {self.tantrumEmote}")
                    return

                # Pull primogem data from the database.
                self.cursor.execute("SELECT primogems, \
                                    (SELECT COUNT(*)+1 FROM wishstats WHERE primogems>x.primogems) AS rankUpper, \
                                    (SELECT COUNT(*) FROM wishstats WHERE primogems>=x.primogems) AS rankLower, \
                                    (SELECT COUNT(*) FROM wishstats) AS userCount \
                                    FROM `wishstats` x WHERE x.userId=%s", (uid,))
                data = self.cursor.fetchone()
                userPrimogems = data[0]
                userRankUpper = data[1]
                userRankLower = data[2]
                userCount = data[3]

                addressingMethod = "you" if targetUser == user else "they"

                bot.send_message(channel, f"{user}, {addressingMethod} have {userPrimogems} primogems and are placed {userRankUpper}/{userCount}. {self.nomEmote}")

            elif firstArg == "top":
                validSecondArgs = ["wishes", "fiftyfiftieswon", "fiftyfiftieslost", "primogems", "primos", "points", "rouletteswon", "rouletteslost", "slotswon", "slotslost"]
                secondArg = None

                try:
                    secondArg = args[2]
                except IndexError:
                    bot.send_message(channel, f"{user}, please provide a second argument to get the top stats for! Valid second arguments are: {' '.join(validSecondArgs)}")
                    return

                if secondArg not in validSecondArgs:
                    bot.send_message(channel, f"{user}, please provide a valid second second argument to get the top stats for! Valid second arguments are: {' '.join(validSecondArgs)}")
                    return

                if secondArg == "wishes":
                    self.cursor.execute("SELECT username, wishesDone FROM wishstats ORDER BY wishesDone DESC LIMIT 10")
                    result = self.cursor.fetchmany(10)

                    targetStr = ""

                    currentLoopCount = 0
                    for data in result:
                        currentLoopCount += 1

                        targetStr += f"{data[0]}_({data[1]})"
                        if currentLoopCount < len(result):
                            targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                    
                    bot.send_message(channel, targetStr)
                elif secondArg == "fiftyfiftieswon":
                    self.cursor.execute("SELECT username, fiftyFiftiesWon FROM wishstats ORDER BY fiftyFiftiesWon DESC LIMIT 10")
                    result = self.cursor.fetchmany(10)

                    targetStr = ""

                    currentLoopCount = 0
                    for data in result:
                        currentLoopCount += 1

                        targetStr += f"{data[0]}_({data[1]})"
                        if currentLoopCount < len(result):
                            targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                    
                    bot.send_message(channel, targetStr)
                elif secondArg == "fiftyfiftieslost":
                    self.cursor.execute("SELECT username, fiftyFiftiesLost FROM wishstats ORDER BY fiftyFiftiesLost DESC LIMIT 10")
                    result = self.cursor.fetchmany(10)

                    targetStr = ""

                    currentLoopCount = 0
                    for data in result:
                        currentLoopCount += 1

                        targetStr += f"{data[0]}_({data[1]})"
                        if currentLoopCount < len(result):
                            targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                    
                    bot.send_message(channel, targetStr)
                elif secondArg in ["primogems", "primos", "points"]:
                    self.cursor.execute("SELECT username, primogems FROM wishstats ORDER BY primogems DESC LIMIT 10")
                    result = self.cursor.fetchmany(10)

                    targetStr = ""

                    currentLoopCount = 0
                    for data in result:
                        currentLoopCount += 1

                        targetStr += f"{data[0]}_({data[1]})"
                        if currentLoopCount < len(result):
                            targetStr += ", " # Separate results with a comma if we're not at the end of the data.
                    
                    bot.send_message(channel, targetStr)
                elif secondArg in "rouletteswon":
                   self.cursor.execute("SELECT username, roulettesWon FROM gamblestats ORDER BY roulettesWon DESC LIMIT 10")
                   result = self.cursor.fetchmany(10)

                   targetStr = ""

                   currentLoopCount = 0
                   for data in result:
                       currentLoopCount += 1

                       targetStr += f"{data[0]}_({data[1]})"
                       if currentLoopCount < len(result):
                           targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                   bot.send_message(channel, targetStr)
                elif secondArg in "rouletteslost":
                   self.cursor.execute("SELECT username, roulettesLost FROM gamblestats ORDER BY roulettesLost DESC LIMIT 10")
                   result = self.cursor.fetchmany(10)

                   targetStr = ""

                   currentLoopCount = 0
                   for data in result:
                       currentLoopCount += 1

                       targetStr += f"{data[0]}_({data[1]})"
                       if currentLoopCount < len(result):
                           targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                   bot.send_message(channel, targetStr)
                elif secondArg in "slotswon":
                   self.cursor.execute("SELECT username, slotsWon FROM gamblestats ORDER BY slotsWon DESC LIMIT 10")
                   result = self.cursor.fetchmany(10)

                   targetStr = ""

                   currentLoopCount = 0
                   for data in result:
                       currentLoopCount += 1

                       targetStr += f"{data[0]}_({data[1]})"
                       if currentLoopCount < len(result):
                           targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                   bot.send_message(channel, targetStr)
                elif secondArg in "slotslost":
                   self.cursor.execute("SELECT username, slotsLost FROM gamblestats ORDER BY slotsWon DESC LIMIT 10")
                   result = self.cursor.fetchmany(10)

                   targetStr = ""

                   currentLoopCount = 0
                   for data in result:
                       currentLoopCount += 1

                       targetStr += f"{data[0]}_({data[1]})"
                       if currentLoopCount < len(result):
                           targetStr += ", " # Separate results with a comma if we're not at the end of the data.

                   bot.send_message(channel, targetStr)

            elif firstArg in ["pity", "pitycheck", "pitycounter"]:
                targetUser = user
                try:
                    targetUser = args[2]
                except IndexError:
                    pass

                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, {'you' if targetUser == user else 'they'} are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show pity due to a Twitch API error! {self.tantrumEmote}")
                    return

                self.cursor.execute("SELECT characterBannerPityCounter, weaponBannerPityCounter, standardBannerPityCounter, wishesSinceLast4StarOnCharacterBanner, \
                wishesSinceLast4StarOnWeaponBanner, wishesSinceLast4StarOnStandardBanner FROM wishstats WHERE userId=%s", (uid,))
                results = self.cursor.fetchone()

                addressingMethod = "Your" if targetUser == user else "Their"

                bot.send_message(channel, f"{user}, {addressingMethod} current pity counters - Character: {results[0]} | Weapon: {results[1]} | Standard: {results[2]} {self.neutralEmote} \
                Wishes since last 4 star - Character: {results[3]} | Weapon: {results[4]} | Standard: {results[5]} {self.primogemEmote}")
            elif firstArg == "stats":
                targetUser = user
                try:
                    targetUser = args[2]
                except IndexError:
                    pass

                targetUser = targetUser.strip("@,")

                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, {'you are not registered!' if targetUser == user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show stats due to a Twitch API error! {self.tantrumEmote}")
                    return

                self.cursor.execute("SELECT wishesDone, fiftyFiftiesWon, fiftyFiftiesLost, owned5StarCharacters, owned5StarWeapons, owned4StarCharacters, owned4StarWeapons, primogems FROM wishstats WHERE userId=%s", (uid,))
                results = self.cursor.fetchone()

                wishesDone = results[0]
                fiftyFiftiesWon = results[1]
                fiftyFiftiesLost = results[2]
                owned5StarCharacters = json.loads(results[3])
                owned5StarWeapons = json.loads(results[4])
                owned4StarCharacters = json.loads(results[5])
                owned4StarWeapons = json.loads(results[6])
                userPrimogems = results[7]

                self.cursor.execute("SELECT tradesDone FROM tradestats WHERE userId=%s", (uid,))
                tradesDone = self.cursor.fetchone()[0]

                self.cursor.execute("SELECT duelsWon, duelsLost FROM duelstats WHERE userId=%s", (uid,))
                duelData = self.cursor.fetchone()
                duelsWon = duelData[0]
                duelsLost = duelData[1]

                self.cursor.execute("SELECT roulettesWon, roulettesLost, slotsWon, slotsLost FROM gamblestats WHERE userId=%s", (uid,))
                gambleData = self.cursor.fetchone()
                roulettesWon = gambleData[0]
                roulettesLost = gambleData[1]
                slotsWon = gambleData[2]
                slotsLost = gambleData[3] 

                addressingMethod = "You" if targetUser == user else "They"

                bot.send_message(channel, f"{user}, {addressingMethod} currently have {userPrimogems} primogems and have done {wishesDone} wishes so far. {addressingMethod} won {fiftyFiftiesWon} 50-50s and lost {fiftyFiftiesLost}. \
                {addressingMethod} own {len(owned5StarCharacters)} 5 star characters, {len(owned5StarWeapons)} 5 star weapons, {len(owned4StarCharacters)} 4 star characters \
                and {len(owned4StarWeapons)} 4 star weapons. {addressingMethod} have done {tradesDone} successful trades. {addressingMethod} won {duelsWon} duels and \
                lost {duelsLost} duels. Roulette W/L: {roulettesWon}/{roulettesLost} Slots W/L:{slotsWon}/{slotsLost} {self.proudEmote}")
            elif firstArg == "guarantee":
                targetUser = user
                try:
                    targetUser = args[2]
                except IndexError:
                    pass

                userExists = None
                try:
                    userExists = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, {'you are not registered!' if targetUser == user else 'that user is not registered!'} Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show guarantee standings due to a Twitch API error! {self.tantrumEmote}")
                    return

                self.cursor.execute("SELECT has5StarGuaranteeOnCharacterBanner, has5StarGuaranteeOnWeaponBanner, has4StarGuaranteeOnCharacterBanner, has4StarGuaranteeOnWeaponBanner from wishstats where userId=%s", (uid,))
                result = self.cursor.fetchone()

                has5StarGuaranteeOnCharacterBanner = result[0]
                has5StarGuaranteeOnWeaponBanner = result[1]
                has4StarGuaranteeOnCharacterBanner = result[2]
                has4StarGuaranteeOnWeaponBanner = result[3]

                addressingMethod = "Your" if targetUser == user else "Their"

                positiveEmoji = "✅"
                negativeEmoji = "❌"
                bot.send_message(channel, f"{user}, {addressingMethod} current guarantee standings: Character banner 5 star {positiveEmoji if has5StarGuaranteeOnCharacterBanner else negativeEmoji} | \
                Character banner 4 star {positiveEmoji if has4StarGuaranteeOnCharacterBanner else negativeEmoji} | Weapon banner 5 star {positiveEmoji if has5StarGuaranteeOnWeaponBanner else negativeEmoji} | \
                Weapon banner 4 star {positiveEmoji if has4StarGuaranteeOnWeaponBanner else negativeEmoji}")
            elif firstArg == "help":
                bot.send_message(channel, f"{user}, {self.DESCRIPTION}")
            elif firstArg == "register":
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if userExists:
                    bot.send_message(channel, f"{user}, you are already registered! {self.angryEmote}")
                    return

                self.CreateUserTableEntry(user)

                bot.send_message(channel, f"{user}, you have been registered successfully! {self.proudEmote} You got {self.primogemAmountOnRegistration} primogems as a welcome bonus! {self.primogemEmote}")
            elif firstArg == "overview":
                self.cursor.execute("select SUM(wishesDone), SUM(fiftyFiftiesWon), SUM(fiftyFiftiesLost), COUNT(*) from wishstats;")
                result = self.cursor.fetchone()

                totalWishesDone = result[0]
                totalFiftyFiftiesWon = result[1]
                totalFiftyFiftiesLost = result[2]
                totalUserCount = result[3]

                bot.send_message(channel, f"{totalUserCount} users in the database have collectively done {totalWishesDone} wishes. {totalFiftyFiftiesWon} 50-50s were won \
                out of the total {totalFiftyFiftiesWon + totalFiftyFiftiesLost}. That's a {round((totalFiftyFiftiesWon / (totalFiftyFiftiesWon + totalFiftyFiftiesLost))*100, 2)}% win \
                rate! {self.neutralEmote}")
            elif firstArg == "duel":
                duelTarget = None
                duelAmount = None
                try:
                    duelTarget = args[2]
                    duelAmount = args[3]
                except IndexError:
                    bot.send_message(channel, f"{user}, usage: _genshin duel (username) (amount). {self.thumbsUpEmote}")
                    return
                
                if duelTarget == botUsername:
                    bot.send_message(channel, f"{user}, think you stand a chance against Paimon?! {self.stabEmote}")
                    return
                elif duelTarget == user:
                    bot.send_message(channel, f"{user}, don't be so self-conflicted, love yourself! {self.thumbsUpEmote}")
                    return

                # See if these users are registered.
                isUserRegistered = None
                isTargetRegistered = None

                try:
                    isUserRegistered = self.CheckUserRowExists(user)
                    isTargetRegistered = self.CheckUserRowExists(duelTarget)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not isUserRegistered:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return
                elif not isTargetRegistered:
                    bot.send_message(channel, f"{user}, duel target {duelTarget} is not registered! Get them to use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")         
                    return

                # Get user and target Twitch UIDs.
                userUID = self.GetTwitchUserID(user)
                targetUID = self.GetTwitchUserID(duelTarget)
                
                # Get primogem and in-duel stats relating to both users.
                self.cursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelingWith, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
                userPrimogems = userData[0]
                userInDuel = userData[1]
                userDuelingWith = userData[2]
                userDuelStartTime = userData[3]

                self.cursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelingWith, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (targetUID,))
                targetData = self.cursor.fetchone()
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
                    bot.send_message(channel, f"{user}, couldn't parse the duel amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                    return

                # Do necessary checks before initiating the duel.
                if userInDuel:
                    if int((timeNow - userDuelStartTime).total_seconds()) < self.duelTimeout:  # Since the functionality to timeout the duels would be too costly and unnecessary (and not because I'm lazy kappa), we just check the time differential.
                        bot.send_message(channel, f"{user}, you are already dueling with {userDuelingWith}! {self.angryEmote}")
                        return
                elif targetInDuel:
                    if int((timeNow - targetDuelStartTime).total_seconds()) < self.duelTimeout:
                        bot.send_message(channel, f"{user}, {duelTarget} is currently dueling with {targetDuelingWith}! {self.sadEmote}")
                        return
                elif userPrimogems < duelAmount:
                    bot.send_message(channel, f"{user}, you only have {userPrimogems} primogems! {self.shockedEmote}")
                    return
                elif targetPrimogems < duelAmount:
                    bot.send_message(channel, f"{user}, {duelTarget} only has {targetPrimogems} primogems! {self.shockedEmote}")
                    return
                
                # No problems were found, the duel is on!

                # Update duelstats entries for both users.
                self.cursor.execute("UPDATE duelstats SET inDuel=TRUE, duelingWith=%s, duelAmount=%s, duelStartTime=NOW(), isInitiator=TRUE WHERE userId=%s", (duelTarget, duelAmount, userUID))
                self.database.commit()
                self.cursor.execute("UPDATE duelstats SET inDuel=TRUE, duelingWith=%s, duelAmount=%s, duelStartTime=NOW(), isInitiator=FALSE WHERE userId=%s", (user, duelAmount, targetUID))
                self.database.commit()

                # Announce the duel in the chat.
                bot.send_message(channel, f"{duelTarget}, {user} wants to duel you for {duelAmount} primogems! You can use _genshin duelaccept or _genshin dueldeny to respond within {self.duelTimeout} seconds! {self.stabEmote}")
            elif firstArg == "duelaccept":
                userUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"Can not proceed due to a Twitch API problem. {self.sadEmote}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return
                
                if not userExists:
                    bot.send_message(channel, f"{user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                # See if the user is in a valid duel and get their primogem data.
                self.cursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelAmount, duelstats.duelingWith, duelstats.isInitiator, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
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
                            bot.send_message(channel, f"You can't accept the duel you started! You have to wait for {duelingWith} to accept the duel or wait until the timeout! {self.angryEmote}")
                            return
                        
                        targetUID = None
                        try:
                            targetUID = self.GetTwitchUserID(duelingWith)
                        except:
                            bot.send_message(channel, f"{user}, cannot proceed due to a Twitch API error. Try again in a bit. {self.shockedEmote}")
                            return

                        # Get opponent's primogem data.
                        self.cursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (targetUID,))
                        opponentPrimogems = self.cursor.fetchone()[0]

                        # See if both sides still have enough primogems. If not, cancel the duel.
                        if userPrimogems < duelAmount:
                            bot.send_message(channel, f"{user}, you don't have the same amount of primogems you had at the time of duel's start - the duel will be cancelled. {self.loserEmote}")

                            self.cursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                            self.database.commit()
                            return
                        elif opponentPrimogems < duelAmount:
                            bot.send_message(channel, f"{user}, {duelingWith} doesn't have the same amount of primogems they had at the time of duel's start - the duel will be cancelled. {self.loserEmote}")
                
                            self.cursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                            self.database.commit()
                            return
                        
                        # Duel begins!
                        duelists = [user, duelingWith]
                        winner = random.choice(duelists)
                        duelists.remove(winner)
                        loser = duelists[0]

                        winnerUID = userUID if winner == user else targetUID
                        loserUID = userUID if winner != user else targetUID

                        # Update primogems.
                        self.cursor.execute("UPDATE wishstats SET primogems = (CASE WHEN userId=%s THEN primogems+%s WHEN userId=%s THEN primogems-%s END) WHERE userID IN (%s, %s)", (winnerUID, duelAmount, loserUID, duelAmount, userUID, targetUID))
                        self.database.commit()

                        # Update duels won/lost stats.
                        self.cursor.execute("UPDATE duelstats SET duelsWon=duelsWon+1 WHERE userId=%s", (winnerUID,))
                        self.database.commit()
                        self.cursor.execute("UPDATE duelstats SET duelsLost=duelsLost+1 WHERE userId=%s", (loserUID,))
                        self.database.commit()

                        # These people are not in a duel anymore now that it's over, update this change in the database.
                        self.cursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                        self.database.commit()

                        # Announce the winner.
                        bot.send_message(channel, f"{winner} {self.danceEmote} won the duel against {loser} {self.loserEmote} for {duelAmount} primogems!")
                    else:
                        bot.send_message(channel, f"{user}, you have no active duels to accept. {self.sadEmote}")
                        return
                else:
                    bot.send_message(channel, f"{user}, you have no active duels to accept. {self.sadEmote}")
                    return

            elif firstArg == "dueldeny":
                userUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"Cannot proceed due to a Twitch API problem. {self.sadEmote}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return
                
                if not userExists:
                    bot.send_message(channel, f"{user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                # See if the user is in a valid duel and get their primogem data.
                self.cursor.execute("SELECT wishstats.primogems, duelstats.inDuel, duelstats.duelAmount, duelstats.duelingWith, duelstats.isInitiator, duelstats.duelStartTime FROM wishstats NATURAL JOIN duelstats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
                inDuel = userData[1]
                duelingWith = userData[3]
                isInitiator = userData[4]
                duelStartTime = userData[5]      
                
                timeNow = datetime.datetime.now()

                targetUID = None
                try:
                    targetUID = self.GetTwitchUserID(duelingWith)
                except:
                    bot.send_message(channel, f"Cannot proceed due to a Twitch API problem. {self.sadEmote}")
                    return

                if inDuel:
                    if int((timeNow - duelStartTime).total_seconds()) < self.duelTimeout and not isInitiator:
                        # Valid duel, move on with the denial.
                        self.cursor.execute("UPDATE duelstats SET inDuel=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                        self.database.commit()

                        bot.send_message(channel, f"{duelingWith}, {user} denied your duel request. {self.shockedEmote}")
                    else:
                        bot.send_message(channel, f"{user}, you have no active duels to deny! {self.angryEmote}")
                        return
                else:
                    bot.send_message(channel, f"{user}, you have no active duels to deny! {self.angryEmote}")
                    return
            
            elif firstArg in ["give", "giveprimos", "giveprimogems"]:            
                giveTarget = None
                giveAmount = None
                try:
                    giveTarget = args[2]
                    giveAmount = args[3]
                except IndexError:
                    bot.send_message(channel, f"{user}, usage: _genshin {firstArg} (username) (amount). {self.thumbsUpEmote}")
                    return

                if giveTarget == user:
                    bot.send_message(channel, f"{user}, you gave yourself your own {giveAmount} primogems and you now have exactly the same amount. Paimon approves! {self.thumbsUpEmote}")
                    return
                elif giveTarget == botUsername:
                    bot.send_message(channel, f"{user}, Paimon appreciates the gesture, but she'd prefer if you kept your points. {self.shyEmote}")
                    return
                
                # See if these users are registered.
                isUserRegistered = None
                isTargetRegistered = None

                try:
                    isUserRegistered = self.CheckUserRowExists(user)
                    isTargetRegistered = self.CheckUserRowExists(giveTarget)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not isUserRegistered:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return
                elif not isTargetRegistered:
                    bot.send_message(channel, f"{user}, target {giveTarget} is not registered! Get them to use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")         
                    return

                userUID = None
                targetUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                    targetUID = self.GetTwitchUserID(giveTarget)
                except:
                    bot.send_message(channel, f"{user}, cannot proceed due to a Twitch API error. {self.sadEmote}")
                    return

                # See if the user has enough primogems.
                self.cursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (userUID,))
                userPrimogems = self.cursor.fetchone()[0]

                try:
                    giveAmount = int(giveAmount)
                except ValueError:
                    giveAmount = self.GetUserPrimogemsPartial(userPrimogems, giveAmount)

                if giveAmount == -1:
                    bot.send_message(channel, f"{user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                    return

                # Reject invalid amounts.
                if giveAmount <= 0:
                    bot.send_message(channel, f"{user}, Paimon thinks {giveTarget} would appreciate it more if you gave them a positive amount of primogems! {self.angryEmote}")
                    return

                if userPrimogems < giveAmount:
                    bot.send_message(channel, f"{user}, you only have {userPrimogems} primogems! {self.sadEmote}")
                    return
                
                # Update primogems.
                self.cursor.execute("UPDATE wishstats SET primogems = (CASE WHEN userId=%s THEN primogems+%s WHEN userId=%s THEN primogems-%s END) WHERE userId IN (%s, %s)", (targetUID, giveAmount, userUID, giveAmount, userUID, targetUID))
                self.database.commit()

                # Announce the successful exchange.
                bot.send_message(channel, f"{user} gave {giveAmount} primogems to {giveTarget}! {self.shyEmote}")

            elif firstArg == "trade":
                validItemTypes = ["character", "weapon"]

                # First, check if the syntax is correct.
                targetUser = None
                itemType = None
                itemName = None
                primogemOffer = None

                try:
                    targetUser = args[2]
                    itemType = args[3]
                    primogemOffer = args[-1]
                except IndexError:
                    bot.send_message(channel, f"{user}, usage: _genshin {firstArg} username character/weapon \"Item Name\" primogemOfferAmount {self.derpEmote}")
                    return
                
                if itemType not in validItemTypes:
                    bot.send_message(channel, f"{user}, {itemType} is not a valid item type! {self.tantrumEmote} Valid item types are: {' '.join(validItemTypes)} | \
                                                Example command usage: _genshin {firstArg} username character/weapon \"Item Name\" primogemOfferAmount {self.derpEmote}")
                    return

                try:
                    itemName = re.findall('"([^"]*)"', message)[0]
                except IndexError:
                    bot.send_message(channel, f"{user}, no item name in double quotation marks (\") was found! Make sure to include it in the command. Usage example: \
                                                _genshin {firstArg} username character/weapon \"Item Name\" primogemOfferAmount {self.derpEmote}")
                    return

                # Check if these users exist in the database.
                userExistsInDatabase = None
                targetExistsInDatabase = None

                try:
                    userExistsInDatabase = self.CheckUserRowExists(user)
                    targetExistsInDatabase = self.CheckUserRowExists(targetUser)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExistsInDatabase:
                    bot.send_message(channel, f"{user}, you are not registered! Use _genshin register to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return
                elif not targetExistsInDatabase:
                    bot.send_message(channel, f"{user}, {targetUser} is not registered! Get them to use _genshin register to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                # Get the Twitch UIDs for both users.
                userUID = None
                targetUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                    targetUID = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, cannot proceed due a to a Twitch API error. {self.sadEmote}")
                    return

                # See if any of the users is in an active trade.
                self.cursor.execute("SELECT inTrade, tradingWith, tradeStartTime FROM tradestats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
                userInTrade = userData[0]
                userTradingWith = userData[1]
                userTradeStartTime = userData[2]

                self.cursor.execute("SELECT inTrade, tradingWith, tradeStartTime FROM tradestats WHERE userId=%s", (targetUID,))
                targetData = self.cursor.fetchone()
                targetInTrade = targetData[0]
                targetTradingWith = targetData[1]
                targetTradeStartTime = targetData[2]

                timeNow = datetime.datetime.now()

                if userInTrade:
                    if int((timeNow - userTradeStartTime).total_seconds()) < self.tradeTimeout:
                        bot.send_message(channel, f"{user}, you are already in an active trade with {userTradingWith}! {self.angryEmote}")
                        return
                elif targetInTrade:
                    if int((timeNow - targetTradeStartTime).total_seconds()) < self.tradeTimeout:
                        bot.send_message(channel, f"{user}, {targetUser} is in an active trade with {targetTradingWith}! {self.shockedEmote}")
                        return
            
                # See if the user has enough primogems.
                self.cursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (userUID,))
                userPrimogems = self.cursor.fetchone()[0]

                try:
                    primogemOffer = int(args[-1])
                except ValueError:
                    primogemOffer = self.GetUserPrimogemsPartial(userPrimogems, primogemOffer)
                    
                if primogemOffer == -1:
                    bot.send_message(channel, f"{user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                    return

                if userPrimogems < primogemOffer:
                    bot.send_message(channel, f"{user}, you only have {userPrimogems} primogems! {self.shockedEmote}")
                    return

                # Check for abnormalities.
                if primogemOffer < 0:
                    bot.send_message(channel, f"{user}, primogem offer amount cannot be less than zero! {self.shockedEmote}")
                    return
                elif targetUser == user:
                    bot.send_message(channel, f"{user}, you successfully traded your own {itemName} with yourself! Paimon thinks that was a good trade! {self.thumbsUpEmote}")
                    return
                elif targetUser == botUsername:
                    bot.send_message(channel, f"{user}, thanks for the offer, but Paimon doesn't know how trading math works. {self.derpEmote}")
                    return

                # Check if the trade initiator has already maxed out the aformentioned item. If they do, don't let them initiate the trade.
                userOwnedItemData = None
                if itemType == "character":
                    self.cursor.execute("SELECT owned5StarCharacters, owned4StarCharacters FROM wishstats where userId=%s", (userUID,))
                else:
                    self.cursor.execute("SELECT owned5StarWeapons, owned4StarWeapons FROM wishstats where userId=%s", (userUID,))

                userOwnedItemData = self.cursor.fetchone()
                userOwned5Stars = json.loads(userOwnedItemData[0])
                userOwned4Stars = json.loads(userOwnedItemData[1])

                userConstellationOrRefinementValue = None

                if itemName in userOwned5Stars:
                    userConstellationOrRefinementValue = userOwned5Stars[itemName]
                elif itemName in userOwned4Stars:
                    userConstellationOrRefinementValue = userOwned4Stars[itemName]

                if userConstellationOrRefinementValue is not None and (userConstellationOrRefinementValue == "C6" or userConstellationOrRefinementValue == "R5"):
                    bot.send_message(channel, f"{user}, You already have {itemName} at {userConstellationOrRefinementValue}, which is already the maximum value for the \"{itemType}\" type! {self.angryEmote}")
                    return

                # See if the target has the amentioned item.
                targetOwnedItemData = None
                if itemType == "character":
                    self.cursor.execute("SELECT owned5StarCharacters, owned4StarCharacters FROM wishstats where userId=%s", (targetUID,))
                else:
                    self.cursor.execute("SELECT owned5StarWeapons, owned4StarWeapons FROM wishstats where userId=%s", (targetUID,))

                targetOwnedItemData = self.cursor.fetchone()
                targetOwned5Stars = json.loads(targetOwnedItemData[0])
                targetOwned4Stars = json.loads(targetOwnedItemData[1])

                itemStarValue = None
                constellationOrRefinementValue = None
                if itemName in targetOwned5Stars:
                    itemStarValue = "5star"
                    constellationOrRefinementValue = targetOwned5Stars[itemName]
                elif itemName in targetOwned4Stars:
                    itemStarValue = "4star"
                    constellationOrRefinementValue = targetOwned4Stars[itemName]
                else:
                    bot.send_message(channel, f"{user}, {targetUser} does not own any {itemType}s called \"{itemName}\"! {self.tantrumEmote}")
                    return

                # Everything is in order, the trade is initiated!
                self.cursor.execute("UPDATE tradestats SET inTrade=TRUE, isBuying = \
                                                                    (CASE WHEN userId=%s THEN TRUE \
                                                                    WHEN userId=%s THEN FALSE END), \
                                                                    isCharacter=%s, item=%s, itemStarValue=%s, quality=%s, tradingWith = \
                                                                    (CASE WHEN userId=%s THEN %s \
                                                                    WHEN userId=%s THEN %s END), \
                                                                    primogemOffer=%s, tradeStartTime=NOW() WHERE userId IN (%s, %s)",
                                                                    (userUID, targetUID, (True if itemType == "character" else False), itemName, itemStarValue,
                                                                    constellationOrRefinementValue, userUID, targetUser, targetUID, user, primogemOffer, userUID, targetUID))
                self.database.commit()

                starInt = 5 if itemStarValue == "5star" else 4

                # Announce the trade offer in the chat.
                bot.send_message(channel, f"{targetUser}, {user} is offering {primogemOffer} {'primogem' if primogemOffer == 1 else 'primogems'} for your \
                {itemName}({starInt}⭐)[{constellationOrRefinementValue}]! You can use _genshin tradeaccept or _genshin tradedeny to respond within {self.tradeTimeout} seconds. {self.nomEmote}")
            
            elif firstArg == "tradeaccept":
                userUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"Can not proceed due to a Twitch API problem. {self.sadEmote}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return
                
                if not userExists:
                    bot.send_message(channel, f"{user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                # See if the user is in a valid trade and get their primogem data.
                self.cursor.execute("SELECT wishstats.primogems, tradestats.inTrade, tradestats.isBuying, tradestats.isCharacter, tradestats.item, tradestats.itemStarValue, \
                tradestats.quality, tradestats.tradingWith, tradestats.primogemOffer, tradestats.tradeStartTime FROM wishstats NATURAL JOIN tradestats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
                userPrimogems = userData[0]
                userInTrade = userData[1]
                userIsBuying = userData[2]
                isCharacter = userData[3]
                itemName = userData[4]
                itemStarValue = userData[5]
                itemQuality = userData[6]
                userTradingWith = userData[7]
                primogemOffer = userData[8]
                tradeStartTime = userData[9]

                timeNow = datetime.datetime.now()

                if userInTrade:
                    if int((timeNow - tradeStartTime).total_seconds()) < self.tradeTimeout:
                        # The trade is valid, we can continue.

                        # The trade initiator cannot accept the trade they started.
                        if userIsBuying:
                            bot.send_message(channel, f"You can't accept the trade you started! You have to wait for {userTradingWith} to accept or deny the trade or wait until the timeout! {self.angryEmote}")
                            return
                        
                        targetUID = None
                        try:
                            targetUID = self.GetTwitchUserID(userTradingWith)
                        except:
                            bot.send_message(channel, f"{user}, cannot proceed due to a Twitch API error. Try again in a bit. {self.shockedEmote}")
                            return

                        # Get trade offerer's primogem data.
                        self.cursor.execute("SELECT primogems FROM wishstats WHERE userId=%s", (targetUID,))
                        offererPrimogems = self.cursor.fetchone()[0]

                        # See if the offerer still has enough primogems. If not, cancel the trade.
                        if offererPrimogems < primogemOffer:
                            bot.send_message(channel, f"{user}, {userTradingWith} has less primogems than the amount they started the trade with. The trade will be cancelled.")
                            
                            self.cursor.execute("UPDATE tradestats SET inTrade=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                            self.database.commit()
                            return
                        
                        # The trade occurs.

                        # Get the relevant item data for the user.
                        if isCharacter:
                            if itemStarValue == "5star":
                                self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (userUID,))
                            else:
                                self.cursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (userUID,))
                        else:
                            if itemStarValue == "5star":
                                self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (userUID,))
                            else:
                                self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (userUID,))
            
                        userItemsData = json.loads(self.cursor.fetchone()[0])

                        userItemsData.pop(itemName)

                        # Edit the item and primogem data for the user.
                        if isCharacter:
                            if itemStarValue == "5star":
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s, owned5StarCharacters=%s WHERE userId=%s", (primogemOffer, json.dumps(userItemsData), userUID))
                            else:
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s, owned4StarCharacters=%s WHERE userId=%s", (primogemOffer, json.dumps(userItemsData), userUID))
                        else:
                            if itemStarValue == "5star":
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s, owned5StarWeapons=%s WHERE userId=%s", (primogemOffer, json.dumps(userItemsData), userUID))
                            else:
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s, owned4StarWeapons=%s WHERE userId=%s", (primogemOffer, json.dumps(userItemsData), userUID))

                        self.database.commit()

                        # Get the characters data for the offerer.
                        if isCharacter:
                            if itemStarValue == "5star":
                                self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (targetUID,))
                            else:
                                self.cursor.execute("SELECT owned4StarCharacters FROM wishstats WHERE userId=%s", (targetUID,))
                        else:
                            if itemStarValue == "5star":
                                self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (targetUID,))
                            else:
                                self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (targetUID,))

                        offererItemsData = json.loads(self.cursor.fetchone()[0])

                        offererItemQuality = None
                        try:
                            offererItemQuality = offererItemsData[itemName]
                        except KeyError: # If the item didn't previously exist before, add it.
                            offererItemsData[itemName] = itemQuality

                        # If an item did exist before, increase its constellation/refinement.
                        if offererItemQuality is not None:
                            if isCharacter:
                                existingConstellation = int(offererItemQuality[-1])
                                newConstellation = existingConstellation + int(itemQuality[-1]) + 1 # Add +1 as a character can be C0 as well.

                                # Prevent the constellation data from going over 6.
                                if newConstellation > 6:
                                    newConstellation = 6

                                offererItemsData[itemName] = "C" + str(newConstellation)
                            else:
                                existingRefinement = int(offererItemQuality[-1])
                                newRefinement = existingRefinement + int(itemQuality[-1])

                                # Prevent the refinement data from going over 5.
                                if newRefinement > 5:
                                    newRefinement = 5
                                
                                offererItemsData[itemName] = "R" + str(newRefinement)
                        
                        # Edit the item and primogem data for the offerer.
                        if isCharacter:
                            if itemStarValue == "5star":
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s, owned5StarCharacters=%s WHERE userId=%s", (primogemOffer, json.dumps(offererItemsData), targetUID))
                            else:
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s, owned4StarCharacters=%s WHERE userId=%s", (primogemOffer, json.dumps(offererItemsData), targetUID))
                        else:
                            if itemStarValue == "5star":
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s, owned5StarWeapons=%s WHERE userId=%s", (primogemOffer, json.dumps(offererItemsData), targetUID))
                            else:
                                self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s, owned4StarWeapons=%s WHERE userId=%s", (primogemOffer, json.dumps(offererItemsData), targetUID))                    
                            
                        self.database.commit()

                        # Trade is complete, so these users are not in a trade anymore - update it so in the database. Also add 1 to their tradesDone counter.
                        self.cursor.execute("UPDATE tradestats SET inTrade=FALSE, tradesDone=tradesDone+1 WHERE userID IN (%s, %s)", (userUID, targetUID))
                        self.database.commit()

                        starInt = 5 if itemStarValue == "5star" else 4

                        targetStr = f"{userTradingWith} bought {itemName}({starInt}⭐)[{itemQuality}] from {user} for {primogemOffer} primogems!"
                        if offererItemsData[itemName] not in ["C0", "R1"]: # If the item got a constellation/refinement upgrade, announce that too. 
                            targetStr += f" Their {itemName} is now {offererItemsData[itemName]}!"
                        
                        targetStr += f" {self.proudEmote}"

                        bot.send_message(channel, targetStr)

            elif firstArg == "tradedeny":
                userUID = None
                try:
                    userUID = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"Cannot proceed due to a Twitch API problem. {self.sadEmote}")
                    return
                
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return
                
                if not userExists:
                    bot.send_message(channel, f"{user}, you are not a registered user! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                # See if the user is in a valid trade.
                self.cursor.execute("SELECT inTrade, isBuying, tradingWith, tradeStartTime FROM tradestats WHERE userId=%s", (userUID,))
                userData = self.cursor.fetchone()
                inTrade = userData[0]
                isBuying = userData[1]
                tradingWith = userData[2]
                tradeStartTime = userData[3]
                
                timeNow = datetime.datetime.now()

                targetUID = None
                try:
                    targetUID = self.GetTwitchUserID(tradingWith)
                except:
                    bot.send_message(channel, f"Cannot proceed due to a Twitch API problem. {self.sadEmote}")
                    return

                if inTrade:
                    if int((timeNow - tradeStartTime).total_seconds()) < self.tradeTimeout:
                        if isBuying:
                            bot.send_message(channel, f"{user}, you can't deny the trade you started! You have to wait for {tradingWith} to respond to the trade or wait until the timeout! {self.angryEmote}")
                            return

                        # Valid trade, move on with the denial.
                        self.cursor.execute("UPDATE tradestats SET inTrade=FALSE WHERE userID IN (%s, %s)", (userUID, targetUID))
                        self.database.commit()

                        bot.send_message(channel, f"{tradingWith}, {user} denied your trade offer. {self.shockedEmote}")
                    else:
                        bot.send_message(channel, f"{user}, you have no active trade offers to deny! {self.angryEmote}")
                        return
                else:
                    bot.send_message(channel, f"{user}, you have no active trade offers to deny! {self.angryEmote}")
                    return

            elif firstArg in ["banner", "banners"]:
                message = ""

                for key, value in self.bannerImageLinks.items():
                    message += f"| {key}: {value} "
                
                bot.send_message(channel, f"{user}, Current banners are: {message}")

            elif firstArg == "update":
                if user != AUTHORIZED_USER:
                    bot.send_message(channel, "🤨")
                    return
                
                self.UpdateFromGist()
                bot.send_message(channel, f"Successfully updated the wish schedule. Current banner names are: {', '.join(self.validBannerNames)}")

            elif firstArg in ["gamble", "roulette"]:
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error.")
                    return

                self.cursor.execute("SELECT primogems FROM wishstats where userId=%s", (uid,))

                result = self.cursor.fetchone()
                ownedPrimogems = result[0]

                betAmount = 0
                try:
                    betAmount = args[2]
                except IndexError:
                    bot.send_message(channel, f"{user}, you haven't entered an amount to bet! Example usage: _genshin roulette all {self.primogemEmote}")
                    return
                
                try:
                    betAmount = int(betAmount)
                except ValueError:
                    # Parse the bet amount value if it can't be parsed to an int.
                    betAmount = self.GetUserPrimogemsPartial(ownedPrimogems, betAmount)

                if betAmount == -1:
                    bot.send_message(channel, f"{user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                    return

                # Check if user has enough primogems.
                if ownedPrimogems < betAmount:
                    bot.send_message(channel, f"{user}, you wanted to bet {betAmount} primogems, but you only have {ownedPrimogems} primogems! {self.angryEmote}")
                    return

                # Now check if user won the roulette.
                randomValue = random.randint(0, 100)
                if randomValue < self.rouletteWinChancePercentage:
                    # User has won the roulette, give them their primogems.
                    earnedPrimogems = betAmount * self.rouletteWinMultiplier

                    self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (earnedPrimogems, uid))
                    self.cursor.execute("UPDATE gamblestats SET roulettesWon=roulettesWon+1 WHERE userId=%s", (uid,))
                    self.database.commit()

                    bot.send_message(channel, f"{user} has won {earnedPrimogems} primogems in roulette, and they now have {earnedPrimogems + ownedPrimogems} primogems! {self.primogemEmote}")
                else:
                    # User has lost the roulette, take their loss from them.
                    lostPrimogems = betAmount

                    self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (lostPrimogems, uid))
                    self.cursor.execute("UPDATE gamblestats SET roulettesLost=roulettesLost+1 WHERE userId=%s", (uid,))
                    self.database.commit()

                    bot.send_message(channel, f"{user} has lost {lostPrimogems} primogems in roulette, and they now have {ownedPrimogems - lostPrimogems} primogems! {self.shockedEmote}")
            
            elif firstArg == "slots":
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error.")
                    return

                self.cursor.execute("SELECT primogems FROM wishstats where userId=%s", (uid,))

                result = self.cursor.fetchone()
                ownedPrimogems = result[0]

                betAmount = 0
                try:
                    betAmount = args[2]
                except IndexError:
                    bot.send_message(channel, f"{user}, you haven't entered an amount to bet! Example usage: _genshin slots all {self.primogemEmote}")
                    return
                
                try:
                    betAmount = int(betAmount)
                except ValueError:
                    # Parse the bet amount value if it can't be parsed to an int.
                    betAmount = self.GetUserPrimogemsPartial(ownedPrimogems, betAmount)

                if betAmount == -1:
                    bot.send_message(channel, f"{user}, couldn't parse the primogem amount! Try inputting a percentile value (like 50%), \"all\", a thousands value like \"10k\", or just plain amount (like 500). {self.derpEmote}")
                    return

                # Check if user has enough primogems.
                if ownedPrimogems < betAmount:
                    bot.send_message(channel, f"{user}, you wanted to bet {betAmount} primogems, but you only have {ownedPrimogems} primogems! {self.angryEmote}")
                    return

                # Now, do the slot rolls!
                firstElement = random.choice(self.slotsElements)
                secondElement = random.choice(self.slotsElements)
                thirdElement = random.choice(self.slotsElements)

                slotsResult = f"{firstElement} | {secondElement} | {thirdElement}"

                # Check for slots win.
                if firstElement == secondElement == thirdElement:
                    earnedPrimogems = betAmount * self.slotsWinMultiplier

                    self.cursor.execute("UPDATE wishstats SET primogems=primogems+%s WHERE userId=%s", (earnedPrimogems, uid))
                    self.cursor.execute("UPDATE gamblestats SET slotsWon=slotsWon+1 WHERE userId=%s", (uid,))
                    self.database.commit()

                    bot.send_message(channel, f"{user} you got {slotsResult} in slots and won {earnedPrimogems} primogems!!! You now have {ownedPrimogems + earnedPrimogems} primogems!!! {self.primogemEmote} {self.primogemEmote} {self.primogemEmote}")
                else:
                    # User has lost the roulette, take their loss from them.
                    lostPrimogems = betAmount

                    self.cursor.execute("UPDATE wishstats SET primogems=primogems-%s WHERE userId=%s", (lostPrimogems, uid))
                    self.cursor.execute("UPDATE gamblestats SET slotsLost=slotsLost+1 WHERE userId=%s", (uid,))
                    self.database.commit()

                    bot.send_message(channel, f"{user} you got {slotsResult} in slots and lost {lostPrimogems} primogems. You now have {ownedPrimogems - lostPrimogems} primogems. {self.sadEmote}")
            
            elif firstArg in "updatename":
                userExists = None
                try:
                    userExists = self.CheckUserRowExists(user)
                except:
                    bot.send_message(channel, f"{user}, can't proceed due to a Twitch API error. {self.sadEmote}")
                    return

                if not userExists:
                    bot.send_message(channel, f"{user}, you are not registered! Use \"_genshin register\" to register and get {self.primogemAmountOnRegistration} primogems! {self.primogemEmote}")
                    return

                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error.")
                    return

                try:
                    userData = requests.get(f"https://api.twitch.tv/helix/channels?broadcaster_id={uid}", headers=TWITCH_API_HEADERS)
                    newUsername = userData.json()["data"][0]["broadcaster_name"]

                    self.cursor.execute("UPDATE wishstats SET username=%s where userId=%s", (newUsername, uid))
                    self.cursor.execute("UPDATE duelstats SET username=%s where userId=%s", (newUsername, uid))
                    self.cursor.execute("UPDATE tradestats SET username=%s where userId=%s", (newUsername, uid))
                    self.cursor.execute("UPDATE gamblestats SET username=%s where userId=%s", (newUsername, uid))
                    self.database.commit()

                    bot.send_message(channel, f"{user}, Successfully updated your new name in the database! {self.proudEmote}")
                except:
                    bot.send_message(channel, f"{user}, An error occured while updating name. {self.sadEmote}")
                    return


