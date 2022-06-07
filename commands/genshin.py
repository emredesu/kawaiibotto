from commands.command import Command
from messagetypes import error, log
from globals import TWITCH_API_HEADERS
import random
import requests
import mysql.connector
import traceback
import datetime
import json

""" 
--- DATABASE STRUCTURE ---
database genshinStats
    table wishstats
        BIGINT userId
        BIGINT wishesDone
        DATETIME lastWishTime
        INT fiftyFiftiesWon
        INT fiftyFiftiesLost
        INT characterBannerPityCounter
        INT weaponBannerPityCounter
        INT standardBannerPityCounter
        BOOL has5StarGuaranteeOnCharacterBanner
        BOOL has5StarGuaranteeOnWeaponBanner
        BOOL has4StarGuaranteeOnCharacterBanner
        BOOL has4StarGuaranteeOnWeaponBanner
        JSON owned5StarCharacters {
            "Kaedehara Kazuha": "C0",
            "Qiqi": "C4",
            "Keqing": "C3"
        }
        JSON owned5StarWeapons {
            "Primordial Jade Winged-Spear": "R1",
            "Aquila Favonius": "R2"
        }
        JSON owned4StarCharacters {
            "Razor": "C1",
            "Yun Jin": "C6",
            "Chongyun": "C4",
            "Yanfei": "C0",
            "Xingqiu": "C5",
            "Noelle": "C20"
        }
        JSON owned4StarWeapons {
            "The Bell": "R5",
            "Favonius Sword": "R2",
            "Rust": "R1"
        }
        INT wishesSinceLast4StarOnCharacterBanner
        INT wishesSinceLast4StarOnWeaponBanner
        INT wishesSinceLast4StarOnStandardBanner
"""

class GenshinCommand(Command):
    COMMAND_NAME = ["genshin", "genshit"]
    COOLDOWN = 0
    DESCRIPTION = "A fully fledged Genshin wish simulator with progress tracking! Use _genshin wish (banner) to wish, _genshin (characters/weapons) to see what you own and _genshin top to see various data, _genshin stats to check your own data, _genshin pity to check your pity counters, _genshin guarantee to check your guarantees and _genshin overview to see global stats. You can add a username at the end of stat commands to check for another user. Every user gets a new wish every 1/2 hour. HungryPaimon"


    successfulInit = True

    requiredSecondsBetweenWishes = 1800

    database = None
    cursor = None

    bannerInfoGistLink = "https://gist.githubusercontent.com/emredesu/2766beb7e57c55b5d0cee9294f96cfa1/raw/kawaiibottoGenshinWishBanners.json"
    emojiAssociationGistLink = "https://gist.githubusercontent.com/emredesu/e13a6274d9ba9825562b279d00bb1c0b/raw/kawaiibottoGenshinEmojiAssociations.json"

    validBannerNames = []
    bannerData = None

    emojiAssociations = None

    # Wish math stuff
    characterBanner5StarHardPity = 90
    characterBanner5StarSoftPityStart = 75
    charaterBanner4StarSoftPityStart = 9

    weaponBanner5StarHardPity = 80
    weaponBanner5StarSoftPityStart = 63
    weaponBanner4StarSoftPityStart = 8

    standardBannerHardPity = 90
    standardBannerSoftPityStart = 75

    characterBanner5StarRateUpProbability = 50
    characterBanner4StarRateUpProbability = 50

    weaponBanner5StarRateUpProbability = 75
    weaponBanner4StarRateUpProbability = 75

    # Character banner
    characterBanner5StarChance = 0.6
    characterBanner4StarChance = 5.1

    # Weapon banner
    weaponBanner5StarChance = 0.7
    weaponBanner4StarChance = 6

    # Standard banner
    standardBanner5StarChance = 0.6
    standardBanner4StarChance = 5.1

    def __init__(self, commands):
        super().__init__(commands)
        self.UpdateFromGist()

        try:
            self.database = mysql.connector.connect(host="localhost", user="root", password="makiisthebestgirl", database="genshinStats")
            self.cursor = self.database.cursor()
        except Exception as e:
            error(f"Fatal error while connecting to the database: {e.__class__.__name__}")
            traceback.print_exc()
            self.successfulInit = False

    def UpdateFromGist(self):
        try:
            jsonData = requests.get(self.bannerInfoGistLink).json()
            self.bannerData = jsonData

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

        # Subtracting two hours from the current time to allow the user to wish after getting registered.
        self.cursor.execute("INSERT INTO wishstats VALUES (%s, %s, 0, SUBTIME(NOW(), \"2:0:0\"), 0, 0, 0, 0, 0, FALSE, FALSE, FALSE, FALSE, \"{}\", \"{}\", \"{}\", \"{}\", 0, 0, 0)", (username, uid))
        self.database.commit()

    # Returns True if the user can wish now, otherwise returns the remaining time until the next wish.
    def GetUserCanWish(self, username):
        uid = self.GetTwitchUserID(username)

        self.cursor.execute("SELECT lastWishTime FROM wishstats where userId=%s", (uid,))

        result = self.cursor.fetchone()
        timeNow = datetime.datetime.now()

        timePassed = timeNow - result[0]
        if timePassed.seconds > self.requiredSecondsBetweenWishes:
            return True
        else:
            return str(datetime.timedelta(seconds=self.requiredSecondsBetweenWishes-timePassed.seconds))

    # Returns the associated emoji(s) if it exists in the JSON, otherwise returns an empty string.
    def GetEmojiAssociation(self, item) -> str:
        try:
            return self.emojiAssociations[item]
        except KeyError:
            return ""

    def execute(self, bot, user, message, channel):
        if not self.successfulInit:
            bot.send_message(channel, "This command has not been initialized properly :c")
            return

        shouldUpdateWishTime = True

        args = message.split()

        validFirstArgs = ["wish", "characters", "weapons", "top", "register", "pity", "pitycheck", "pitycounter", "stats", "guarantee", "help", "overview", "update"]

        firstArg = None
        try:
            firstArg = args[1]
        except IndexError:
            bot.send_message(channel, f"{user}, {self.DESCRIPTION.removeprefix('A fully fledged Genshin wish simulator with progress tracking!')}")
            return

        if firstArg not in validFirstArgs:
            bot.send_message(channel, f"Invalid first argument supplied! Valid first arguments are: {' '.join(validFirstArgs)}")
            return
       
        if firstArg == "wish":
            validSecondArgs = self.validBannerNames
            
            try:
                secondArg = args[2]
            except IndexError:
                bot.send_message(channel, f"Please provide a banner name to wish on. Current banner names are: {' '.join(validSecondArgs)}")
                return

            if secondArg not in validSecondArgs:
                bot.send_message(channel, f"Please provide a valid banner name. Current valid banner names are: {' '.join(validSecondArgs)} | Example usage: _genshin wish {random.choice(validSecondArgs)}")
                return

            if not self.CheckUserRowExists(user):
                bot.send_message(channel, f"{user}, you are not registered! Use _genshin register to register! paimonWhale")
                return

            canUserWish = self.GetUserCanWish(user)

            if type(canUserWish) is bool and canUserWish:
                uid = None
                try:
                    uid = self.GetTwitchUserID(user)
                except:
                    bot.send_message(channel, f"{user}, unable to continue due to a Twitch API error! paimonTantrum")
                    return

                # ----- Character banner -----
                if "character" in secondArg:
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

                    if randomNumber < currentFiveStarChance or currentPityCounter >= self.characterBanner5StarHardPity - 1:
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
                            
                            userString = f"{user}, you beat the 50-50" if not hasGuarantee else f"{user}, you used up your guarantee"
                            userString += f" and got {acquiredCharacter}(5★){self.GetEmojiAssociation(acquiredCharacter)}! HungryPaimon"

                            # Check if the user already has the character.
                            # If they have the character at C6, we'll reset their wish timer.
                            if acquiredCharacter not in characterData:
                                characterData[acquiredCharacter] = "C0"
                            else:
                                if characterData[acquiredCharacter] == "C6":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False
                                    
                                    userString += f" However, you already had {acquiredCharacter} at C6 before, so you get a free wish now instead. paimonHeh"
                                else:
                                    # If they have the character but don't have them at C6, we'll give them a constellation.
                                    newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                    characterData[acquiredCharacter] = newConstellation

                                    userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"

                            # Finally, commit the final changes including guarantee and pity updates.
                            self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=false, characterBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData) ,uid))
                            self.database.commit()

                            # 50-50 win/lose counting
                            if not hasGuarantee:
                                self.cursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                self.database.commit()


                            bot.send_message(channel, userString)    
                        else:
                            # We lost the 5 star 50-50 :/
                            acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                            userString = f"{user}, you lost your 50-50 and got {acquiredCharacter}(5★){self.GetEmojiAssociation(acquiredCharacter)}! paimonTantrum"

                            if acquiredCharacter not in characterData:
                                characterData[acquiredCharacter] = "C0"
                            else:
                                if characterData[acquiredCharacter] == "C6":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredCharacter} at C6 before, you get a free wish now instead. paimonHeh"
                                else:
                                    # If they have the character but don't have them at C6, we'll give them a constellation.
                                    newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                    characterData[acquiredCharacter] = newConstellation

                                    userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"

                            # Finally, commit the final changes including guarantee and pity updates.
                            self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, has5StarGuaranteeOnCharacterBanner=true, characterBannerPityCounter=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (json.dumps(characterData), uid))
                            self.database.commit()

                            bot.send_message(channel, userString)
                    elif (randomNumber > self.characterBanner5StarChance and randomNumber < self.characterBanner5StarChance + self.characterBanner4StarChance) or wishesSinceLast4Star >= 9:
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

                            userString = f"{user}, you won the 50-50" if not hasGuarantee else f"{user}, you used up your 4 star guarantee"
                            userString += f" and got {acquiredCharacter}(4★){self.GetEmojiAssociation(acquiredCharacter)}!"

                            if acquiredCharacter not in characterData:
                                characterData[acquiredCharacter] = "C0"
                            else:
                                if characterData[acquiredCharacter] == "C6":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However you already had {acquiredCharacter} at C6 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the character but don't have them at C6, we'll give them a constellation.
                                    newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                    characterData[acquiredCharacter] = newConstellation

                                    userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"

                            # Update the database with the final data.
                            self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, has4StarGuaranteeOnCharacterBanner=false, wishesSinceLast4StarOnCharacterBanner=0 WHERE userId=%s",
                            (json.dumps(characterData), uid))
                            self.database.commit()

                            # 50-50 win/lose counting
                            if not hasGuarantee:
                                self.cursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                self.database.commit()

                            bot.send_message(channel, userString)
                        else:
                            # We lost the 4 star 50-50 :/
                            userString = f"{user}, you lost the 4 star 50-50"

                            acquiredItem = random.choice(["weapon", "character"])
                            if acquiredItem == "weapon":
                                acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                userString += f" and got {acquiredWeapon}(4★){self.GetEmojiAssociation(acquiredWeapon)}! paimonTantrum"

                                self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                weaponData = json.loads(self.cursor.fetchone()[0])

                                if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Reset wish timer if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Reset the user's wish timer.
                                        self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                        self.database.commit()
                                        shouldUpdateWishTime = False

                                        userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                    
                                # Update the database with the new weapon.
                                self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                self.database.commit()

                                bot.send_message(channel, userString)
                            else:
                                acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                userString += f" and got {acquiredCharacter}(4★){self.GetEmojiAssociation(acquiredCharacter)}! paimonTantrum"

                                if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Reset the user's wish timer.
                                        self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                        self.database.commit()
                                        shouldUpdateWishTime = False

                                        userString += f" However, you already had {acquiredCharacter} at C6 before, so you get a free wish instead. paimonHeh"
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"
                                
                                # Update owned 4 star characters with the updated data.
                                self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                self.database.commit()

                                bot.send_message(channel, userString)

                            # Finally, update the database data to have pity for the next 4 star.
                            self.cursor.execute("UPDATE wishstats SET has4StarGuaranteeOnCharacterBanner=true, wishesSinceLast4StarOnCharacterBanner=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (uid,))
                            self.database.commit()
                        
                    else:
                        acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                        # Increment the pity counters for 4 star and 5 star.
                        self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnCharacterBanner=wishesSinceLast4StarOnCharacterBanner+1, characterBannerPityCounter=characterBannerPityCounter+1 WHERE userId=%s", (uid,))

                        bot.send_message(channel, f"{user}, you got a {acquiredTrash}(3★) QiqiSleep")

                # ----- Standard banner -----                    
                elif "standard" in secondArg:
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

                    if randomNumber < currentFiveStarChance or currentPityCounter >= self.standardBannerHardPity - 1:
                        # We got a 5 star!
                        isCharacter = True if random.choice([0, 1]) == 0 else False
                        if isCharacter:
                            # Get info related to owned 5 star characters.
                            self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
                            characterData = json.loads(retrievedData[0])

                            acquiredCharacter = random.choice(self.bannerData[secondArg]["all5StarCharacters"])

                            userString = f"{user}, you got {acquiredCharacter}(5★){self.GetEmojiAssociation(acquiredCharacter)}! HungryPaimon"

                            if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                            else:
                                if characterData[acquiredCharacter] == "C6":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredCharacter} at C6 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the character but don't have them at C6, we'll give them a constellation.
                                    newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                    characterData[acquiredCharacter] = newConstellation

                                    userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"

                            # Finally, commit the final changes including guarantee and pity updates.
                            self.cursor.execute("UPDATE wishstats SET owned5StarCharacters=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(characterData), uid,))
                            self.database.commit()

                            bot.send_message(channel, userString)
                        else:
                            # Get info related to owned 5 star weapons.
                            self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
                            weaponData = json.loads(retrievedData[0])

                            acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                            userString = f"{user}, you got {acquiredWeapon}(5★){self.GetEmojiAssociation(acquiredWeapon)}! HungryPaimon"

                            if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                            else:
                                # Reset wish timer if the weapon is already maxed out.
                                if weaponData[acquiredWeapon] == "R5":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                    newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                    weaponData[acquiredWeapon] = newRefinement

                                    userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                
                            # Update the database with the new weapon.
                            self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, standardBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                            self.database.commit()

                            bot.send_message(channel, userString)
               
                    elif (randomNumber > self.standardBanner5StarChance and randomNumber < self.standardBanner4StarChance + self.standardBanner5StarChance) or wishesSinceLast4Star >= 9:
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

                            userString = f"{user}, you got {acquiredCharacter}(4★){self.GetEmojiAssociation(acquiredCharacter)}! HungryPaimon"

                            if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                            else:
                                if characterData[acquiredCharacter] == "C6":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredCharacter} at C6 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the character but don't have them at C6, we'll give them a constellation.
                                    newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                    characterData[acquiredCharacter] = newConstellation

                                    userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"

                            # Finally, commit the final changes including guarantee and pity updates.
                            self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(characterData), uid))
                            self.database.commit()

                            bot.send_message(channel, userString)
                        else:
                            # Get info related to owned 4 star weapons.
                            self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                            retrievedData = self.cursor.fetchone()
                            weaponData = json.loads(retrievedData[0])

                            acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                            userString = f"{user}, you got {acquiredWeapon}(4★){self.GetEmojiAssociation(acquiredWeapon)}! HungryPaimon"

                            if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                            else:
                                # Reset wish timer if the weapon is already maxed out.
                                if weaponData[acquiredWeapon] == "R5":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                    newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                    weaponData[acquiredWeapon] = newRefinement

                                    userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                
                            # Update the database with the new weapon.
                            self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, wishesSinceLast4StarOnStandardBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                            self.database.commit()

                            bot.send_message(channel, userString)
                    else:
                        acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                        # Increment the pity counters for 5 star and 4 star.
                        self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnStandardBanner=wishesSinceLast4StarOnStandardBanner+1, standardBannerPityCounter=standardBannerPityCounter+1 WHERE userId=%s", (uid,))

                        bot.send_message(channel, f"{user}, you got a {acquiredTrash}(3★) QiqiSleep") 

                # ----- Weapon banner -----
                else:
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

                    if randomNumber < currentFiveStarChance or currentPityCounter >= self.weaponBanner5StarHardPity - 1:
                        # We got a 5 star!

                        # Get data related to the owned 5 star weapons
                        self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                        weaponData = json.loads(self.cursor.fetchone()[0])

                        # Roll a random chance or see if we have guarantee to check if the 5 star we got is one of the featured ones.
                        if random.uniform(0, 100) < self.weaponBanner5StarRateUpProbability or hasGuarantee5Star:
                            # We got one of the featured weapons!
                            acquiredWeapon = random.choice(self.bannerData[secondArg]["rateUp5StarWeapons"])

                            userString = f"{user}, you beat the odds of 75-25" if not hasGuarantee5Star else f"{user}, you used up your guarantee"
                            userString += f" and got {acquiredWeapon}(5★){self.GetEmojiAssociation(acquiredWeapon)}!"

                            if acquiredWeapon not in weaponData:
                                weaponData[acquiredWeapon] = "R1"
                            else:
                                # Reset wish timer if the weapon is already maxed out.
                                if weaponData[acquiredWeapon] == "R5":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                    newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                    weaponData[acquiredWeapon] = newRefinement

                                    userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                
                            # Update the database with the new weapon.
                            self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=false, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                            self.database.commit()

                            bot.send_message(channel, userString)
                        else:
                            # We lost the 75-25.
                            acquiredWeapon = random.choice(self.bannerData[secondArg]["all5StarWeapons"])

                            userString = f"{user}, You lost the 75-25 and got {acquiredWeapon}(5★){self.GetEmojiAssociation(acquiredWeapon)}! paimonTantrum "

                            if acquiredWeapon not in weaponData:
                                weaponData[acquiredWeapon] = "R1"
                            else:
                                # Reset wish timer if the weapon is already maxed out.
                                if weaponData[acquiredWeapon] == "R5":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                    newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                    weaponData[acquiredWeapon] = newRefinement

                                    userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                
                            # Update the database with the new weapon.
                            self.cursor.execute("UPDATE wishstats SET owned5StarWeapons=%s, has5StarGuaranteeOnWeaponBanner=false, weaponBannerPityCounter=0 WHERE userId=%s", (json.dumps(weaponData), uid,))
                            self.database.commit()

                            bot.send_message(channel, userString)
                    elif (randomNumber > self.weaponBanner5StarChance and randomNumber < self.weaponBanner5StarChance + self.weaponBanner5StarChance) or wishesSinceLast4Star >= 9:
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

                            userString = f"{user}, you won the 50-50" if not hasGuarantee else f"{user}, you used up your 4 star guarantee"
                            userString += f" and got {acquiredWeapon}(4★){self.GetEmojiAssociation(acquiredWeapon)}!"

                            if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                            else:
                                # Reset wish timer if the weapon is already maxed out.
                                if weaponData[acquiredWeapon] == "R5":
                                    # Reset the user's wish timer.
                                    self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                    self.database.commit()
                                    shouldUpdateWishTime = False

                                    userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                else:
                                    # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                    newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                    weaponData[acquiredWeapon] = newRefinement

                                    userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"

                            # Update the database with the final data.
                            self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s, has4StarGuaranteeOnWeaponBanner=false, wishesSinceLast4StarOnWeaponBanner=0 WHERE userId=%s", (json.dumps(weaponData), uid))
                            self.database.commit()

                            # 50-50 win/lose counting
                            if not hasGuarantee:
                                self.cursor.execute("UPDATE wishstats SET fiftyFiftiesWon=fiftyFiftiesWon+1 WHERE userId=%s", (uid,))
                                self.database.commit()

                            bot.send_message(channel, userString)
                        else:
                            # We lost the 4 star 50-50 :/
                            userString = f"{user}, you lost the 4 star 50-50"

                            acquiredItem = random.choice(["weapon", "character"])
                            if acquiredItem == "weapon":
                                acquiredWeapon = random.choice(self.bannerData[secondArg]["all4StarWeapons"])

                                userString += f" and got {acquiredWeapon}(4★){self.GetEmojiAssociation(acquiredWeapon)}! paimonTantrum"

                                self.cursor.execute("SELECT owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                                weaponData = json.loads(self.cursor.fetchone()[0])

                                if acquiredWeapon not in weaponData:
                                    weaponData[acquiredWeapon] = "R1"
                                else:
                                    # Reset wish timer if the weapon is already maxed out.
                                    if weaponData[acquiredWeapon] == "R5":
                                        # Reset the user's wish timer.
                                        self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                        self.database.commit()
                                        shouldUpdateWishTime = False

                                        userString += f" However, you already had {acquiredWeapon} at R5 before, so you get a free wish instead. paimonHeh"
                                    else:
                                        # If they have the weapon but don't have it at R5, we'll give them a refinement.
                                        newRefinement = "R" + str(int(weaponData[acquiredWeapon][-1]) + 1)
                                        weaponData[acquiredWeapon] = newRefinement

                                        userString += f" Your {acquiredWeapon} is now {newRefinement}! paimonHeh"
                                    
                                # Update the database with the new weapon.
                                self.cursor.execute("UPDATE wishstats SET owned4StarWeapons=%s WHERE userId=%s", (json.dumps(weaponData), uid))
                                self.database.commit()

                                bot.send_message(channel, userString)
                            else:
                                self.cursor.execute("SELECT owned4StarCharacters from wishstats WHERE userId=%s", (uid,))
                                characterData = json.loads(self.cursor.fetchone()[0])

                                acquiredCharacter = random.choice(self.bannerData[secondArg]["all4StarCharacters"])

                                userString += f" and got {acquiredCharacter}(4★){self.GetEmojiAssociation(acquiredCharacter)}! paimonTantrum"

                                if acquiredCharacter not in characterData:
                                    characterData[acquiredCharacter] = "C0"
                                else:
                                    if characterData[acquiredCharacter] == "C6":
                                        # Reset the user's wish timer.
                                        self.cursor.execute("UPDATE wishstats SET lastWishTime=SUBTIME(NOW(), '2:0:0') WHERE userId=%s", (uid,))
                                        self.database.commit()
                                        shouldUpdateWishTime = False

                                        userString += f" However, you already had {acquiredCharacter} at C6 before, so you get a free wish instead. paimonHeh"
                                    else:
                                        # If they have the character but don't have them at C6, we'll give them a constellation.
                                        newConstellation = "C" + str(int(characterData[acquiredCharacter][-1]) + 1)
                                        characterData[acquiredCharacter] = newConstellation

                                        userString += f" Your {acquiredCharacter} is now {newConstellation}! paimonHeh"
                                
                                # Update owned 4 star characters with the updated data.
                                self.cursor.execute("UPDATE wishstats SET owned4StarCharacters=%s WHERE userId=%s", (json.dumps(characterData), uid))
                                self.database.commit()

                                bot.send_message(channel, userString)

                            # Finally, update the database data to have pity for the next 4 star.
                            self.cursor.execute("UPDATE wishstats SET has4StarGuaranteeOnWeaponBanner=true, wishesSinceLast4StarOnWeaponBanner=0, fiftyFiftiesLost=fiftyFiftiesLost+1 WHERE userId=%s", (uid,))
                            self.database.commit()                        
                    else:
                        acquiredTrash = random.choice(self.bannerData[secondArg]["all3StarWeapons"])

                        # Increment the pity counters for 4 star and 5 star.
                        self.cursor.execute("UPDATE wishstats SET wishesSinceLast4StarOnWeaponBanner=wishesSinceLast4StarOnWeaponBanner+1, weaponBannerPityCounter=weaponBannerPityCounter+1 WHERE userId=%s", (uid,))

                        bot.send_message(channel, f"{user}, you got a {acquiredTrash}(3★) QiqiSleep")

                if shouldUpdateWishTime:
                    try:
                        self.cursor.execute("UPDATE wishstats SET lastWishTime=NOW(), wishesDone=wishesDone+1 WHERE userId=%s", (self.GetTwitchUserID(user),))
                        self.database.commit()
                    except:
                        # If Twitch API proves problematic, resort back to using user's username.
                        self.cursor.execute("UPDATE wishstats SET lastWishTime=NOW(), wishesDone=wishesDone+1 WHERE username=%s", (user,))
                        self.database.commit()
            else:
                bot.send_message(channel, f"{user}, You cannot wish yet - your next wish will be in: {canUserWish} paimonTantrum")
                return
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

            if not self.CheckUserRowExists(targetUser):
                bot.send_message(channel, f"{user}, {addressingMethod} are not registered! Use _genshin register to register! paimonWhale")
                return
            else:
                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show characters due to a Twitch API error! paimonTantrum")
                    return

                if secondArg == "5star":
                    self.cursor.execute("SELECT owned5StarCharacters FROM wishstats WHERE userId=%s", (uid,))
                    characterData = json.loads(self.cursor.fetchone()[0])

                    if len(characterData.items()) == 0:
                        bot.send_message(channel, f"{user}, {addressingMethod} have no 5 star characters to show. QiqiSleep")
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
                        bot.send_message(channel, f"{user}, {addressingMethod} have no 4 star characters to show. QiqiSleep")
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
        
            if not self.CheckUserRowExists(targetUser):
                bot.send_message(channel, f"{user}, {addressingMethod} are not registered! Use _genshin register to register! paimonWhale")
                return
            else:
                uid = None
                try:
                    uid = self.GetTwitchUserID(targetUser)
                except:
                    bot.send_message(channel, f"{user}, unable to show weapons due to a Twitch API error! paimonTantrum")
                    return

                if secondArg == "5star":
                    self.cursor.execute("SELECT owned5StarWeapons FROM wishstats WHERE userId=%s", (uid,))
                    weaponData = json.loads(self.cursor.fetchone()[0])

                    if len(weaponData.items()) == 0:
                        bot.send_message(channel, f"{user}, {addressingMethod} have no 5 star weapons to show. QiqiSleep")
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
                        bot.send_message(channel, f"{user}, {addressingMethod} have no 4 star weapons to show. QiqiSleep")
                        return

                    targetString = ""

                    currentLoopCount = 0
                    for key, pair in weaponData.items():
                        currentLoopCount += 1

                        targetString += f"{key} ({pair})"
                        
                        if currentLoopCount < len(weaponData.items()):
                            targetString += ", " # Separate characters with a comma if we're not at the end of the list.
                    
                    bot.send_message(channel, f"{user}, {targetString}")        
        elif firstArg == "top":
            validSecondArgs = ["wishes", "fiftyfiftieswon", "fiftyfiftieslost"]
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
        elif firstArg in ["pity", "pitycheck", "pitycounter"]:
            targetUser = user
            try:
                targetUser = args[2]
            except IndexError:
                pass

            if not self.CheckUserRowExists(targetUser):
                bot.send_message(channel, f"{user}, {'you' if targetUser == user else 'they'} are not registered! Use _genshin register to register! paimonWhale")
                return

            uid = None
            try:
                uid = self.GetTwitchUserID(targetUser)
            except:
                bot.send_message(channel, f"{user}, unable to show pity due to a Twitch API error! paimonTantrum")
                return

            self.cursor.execute("SELECT characterBannerPityCounter, weaponBannerPityCounter, standardBannerPityCounter, wishesSinceLast4StarOnCharacterBanner, \
            wishesSinceLast4StarOnWeaponBanner, wishesSinceLast4StarOnStandardBanner FROM wishstats WHERE userId=%s", (uid,))
            results = self.cursor.fetchone()

            addressingMethod = "Your" if targetUser == user else "Their"

            bot.send_message(channel, f"{user}, {addressingMethod} current pity counters - Character: {results[0]} | Weapon: {results[1]} | Standard: {results[2]} HungryPaimon \
            Wishes since last 4 star - Character: {results[3]} | Weapon: {results[4]} | Standard: {results[5]} paimonWhale")
        elif firstArg == "stats":
            targetUser = user
            try:
                targetUser = args[2]
            except IndexError:
                pass

            targetUser = targetUser.strip("@,")

            if not self.CheckUserRowExists(targetUser):
                bot.send_message(channel, f"{user}, {'you are not registered!' if targetUser == user else 'that user is not registered!'} Use _genshin register to register! paimonWhale")
                return

            uid = None
            try:
                uid = self.GetTwitchUserID(targetUser)
            except:
                bot.send_message(channel, f"{user}, unable to show stats due to a Twitch API error! paimonTantrum")
                return

            self.cursor.execute("SELECT wishesDone, fiftyFiftiesWon, fiftyFiftiesLost, owned5StarCharacters, owned5StarWeapons, owned4StarCharacters, owned4StarWeapons FROM wishstats WHERE userId=%s", (uid,))
            results = self.cursor.fetchone()

            wishesDone = results[0]
            fiftyFiftiesWon = results[1]
            fiftyFiftiesLost = results[2]
            owned5StarCharacters = json.loads(results[3])
            owned5StarWeapons = json.loads(results[4])
            owned4StarCharacters = json.loads(results[5])
            owned4StarWeapons = json.loads(results[6])

            addressingMethod = "You" if targetUser == user else "They"

            bot.send_message(channel, f"{user}, {addressingMethod} have done {wishesDone} wishes so far. {addressingMethod} won {fiftyFiftiesWon} 50-50s and lost {fiftyFiftiesLost}. \
            {addressingMethod} own {len(owned5StarCharacters)} 5 star characters, {len(owned5StarWeapons)} 5 star weapons, {len(owned4StarCharacters)} 4 star characters \
            and {len(owned4StarWeapons)} 4 star weapons. paimonHeh")
        elif firstArg == "guarantee":
            targetUser = user
            try:
                targetUser = args[2]
            except IndexError:
                pass

            if not self.CheckUserRowExists(targetUser):
                bot.send_message(channel, f"{user}, {'you are not registered!' if targetUser == user else 'that user is not registered!'} Use _genshin register to register! paimonWhale")
                return

            uid = None
            try:
                uid = self.GetTwitchUserID(targetUser)
            except:
                bot.send_message(channel, f"{user}, unable to show guarantee standings due to a Twitch API error! paimonTantrum")
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
            if self.CheckUserRowExists(user):
                bot.send_message(channel, f"{user}, you are already registered! paimonEHE")
                return

            self.CreateUserTableEntry(user)

            bot.send_message(channel, f"{user}, you have been registered successfully! paimonHeh")
        elif firstArg == "overview":
            self.cursor.execute("select SUM(wishesDone), SUM(fiftyFiftiesWon), SUM(fiftyFiftiesLost), COUNT(*) from wishstats;")
            result = self.cursor.fetchone()

            totalWishesDone = result[0]
            totalFiftyFiftiesWon = result[1]
            totalFiftyFiftiesLost = result[2]
            totalUserCount = result[3]

            bot.send_message(channel, f"{totalUserCount} users in the database have collectively done {totalWishesDone} wishes. {totalFiftyFiftiesWon} 50-50s were won \
            out of the total {totalFiftyFiftiesWon + totalFiftyFiftiesLost}. That's a {round((totalFiftyFiftiesWon / (totalFiftyFiftiesWon + totalFiftyFiftiesLost))*100, 2)}% win \
            rate! HungryPaimon")

        elif firstArg == "update":
            if user != "emredesu":
                bot.send_message(channel, "🤨")
                return
            
            self.UpdateFromGist()
            bot.send_message(channel, f"Successfully updated the wish schedule. Current banner names are: {', '.join(self.validBannerNames)}")
