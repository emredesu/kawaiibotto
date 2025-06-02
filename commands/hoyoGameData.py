from commands.command import Command, WhisperComand
from messageParser import TwitchIRCMessage
from globals import GENSHIN_MYSQL_DB_HOST, GENSHIN_MYSQL_DB_USERNAME, GENSHIN_MYSQL_DB_PASSWORD, GENSHIN_DB_POOL_SIZE, AUTHORIZED_USER, kawaiibottoHoyolabCookies, kawaiibottoGenshinUID, kawaiibottoStarRailUID
import mysql.connector
import mysql.connector.pooling
from messagetypes import error, log
from typing import List, Union
import genshin
import asyncio
import datetime
import time

hoyoDBConnectionPool = mysql.connector.pooling.MySQLConnectionPool(host=GENSHIN_MYSQL_DB_HOST, user=GENSHIN_MYSQL_DB_USERNAME, password=GENSHIN_MYSQL_DB_PASSWORD, database="hoyolabData", pool_size=GENSHIN_DB_POOL_SIZE)

async def GetHoyoClient(messageData: TwitchIRCMessage) -> Union[genshin.Client, None]:
	dbConnection = hoyoDBConnectionPool.get_connection()
	dbCursor = dbConnection.cursor()
	dbCursor.execute("SELECT ltuid, ltoken, ltmid FROM hoyolabData WHERE userID=%s", (int(messageData.tags["user-id"]),))
	result = dbCursor.fetchone()

	try:
		cookies = {"ltuid_v2": int(result[0]), "ltoken_v2": result[1], "ltmid_v2": result[2]}
		client = genshin.Client(cookies)
		hoyolabUser = await client.get_hoyolab_user() # Call an API function to ensure the cookies are valid.
		return client
	except:
		return None
	finally:
		dbConnection.close()
	
async def GetKawaiibottoHoyoClient() -> genshin.Client:
	return genshin.Client(kawaiibottoHoyolabCookies)

async def GetGameAccountUID(client : genshin.Client, gameName : str) -> Union[int, None]:
	highestAccountLevel = 0
	highestLevelAccount = None

	gameAccounts = await client.get_game_accounts()

	for account in gameAccounts:
		if gameName == account.game_biz and "玩家" not in account.nickname: # "玩家" seems to refer to invalid characters that are not yet complete yet (haven't progressed enough in the game), so we ignore those.
			if account.level > highestAccountLevel:
				highestAccountLevel = account.level
				highestLevelAccount = account
	
	if highestLevelAccount is not None:
		return highestLevelAccount.uid

class HoyolabRegistrationWhisperCommand(WhisperComand):
	COMMAND_NAME = "hoyoregister"
	COOLDOWN = 5
	DESCRIPTION = "Register your HoyoLAB cookies for easy access to game energy info for and daily claims for Hoyoverse games!"

	def execute(self, bot, messageData: TwitchIRCMessage):
		ltuid = ""
		ltoken = ""
		ltmid = ""

		args = messageData.whisperContent.split()

		for arg in args:
			if arg.startswith("ltuid:"):
				ltuid = arg[6::]
			elif arg.startswith("ltmid:"):
				ltmid = arg[6::]
			elif arg.startswith("ltoken:"):
				ltoken = arg[7::]

		if ltuid == "" or ltmid == "" or ltoken == "":
			bot.send_whisper(messageData, f"Invalid registration structure. Should be as follows: _hoyoregister ltuid:(ltuid) ltmid:(ltmid) ltoken:(ltoken) ➡️ Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
		dbConnection = hoyoDBConnectionPool.get_connection()
		dbCursor = dbConnection.cursor()

		dbCursor.execute("INSERT INTO hoyolabData VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ltuid=VALUES(ltuid), ltmid=VALUES(ltmid), ltoken=VALUES(ltoken)", 
				   		(int(messageData.tags["user-id"]), messageData.whisperUser, ltuid, ltmid, ltoken))
		dbConnection.commit()

		bot.send_whisper(messageData, f"Successfully registered your HoyoLAB cookies! You may now use all the commands related to Hoyo games. If you entered any values incorrectly, you may use this command again to fix them.")
		dbConnection.close()

class HoyolabRegistrationCommand(Command):
	COMMAND_NAME = "hoyoregister"
	COOLDOWN = 5
	DESCRIPTION = "Register your HoyoLAB cookies for easy access to game energy info for and daily claims for Hoyoverse games!"

	def execute(self, bot, messageData: TwitchIRCMessage):
		ltuid = ""
		ltoken = ""
		ltmid = ""

		args = messageData.content.split()

		for arg in args:
			if arg.startswith("ltuid:"):
				ltuid = arg[6::]
			elif arg.startswith("ltmid:"):
				ltmid = arg[6::]
			elif arg.startswith("ltoken:"):
				ltoken = arg[7::]

		if ltuid == "" or ltmid == "" or ltoken == "":
			bot.send_message(messageData.channel, f"{messageData.user}, Invalid registration structure. Should be as follows: _hoyoregister ltuid:(ltuid) ltmid:(ltmid) ltoken:(ltoken) ➡️ Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
		dbConnection = hoyoDBConnectionPool.get_connection()
		dbCursor = dbConnection.cursor()

		dbCursor.execute("INSERT INTO hoyolabData VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ltuid=VALUES(ltuid), ltmid=VALUES(ltmid), ltoken=VALUES(ltoken)", 
				   		(int(messageData.tags["user-id"]), messageData.user, ltuid, ltmid, ltoken))
		dbConnection.commit()

		bot.send_message(messageData.channel, f"{messageData.user}, Successfully registered your HoyoLAB cookies! You may now use all the commands related to Hoyo games. If you entered any values incorrectly, you may use this command again to fix them.")
		dbConnection.close()

class GenshinResinCheckCommand(Command):
	COMMAND_NAME = ["genshinresin", "resin", "resincheck"]
	COOLDOWN = 5
	DESCRIPTION = "Check your real-time remaining resin! Requires HoyoLAB cookies to function. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md"

	GENSHIN_GAME_NAME = "hk4e_global"
	GENSHIN_EMOTE = "HungryPaimon"

	async def GetGenshinNotes(self, client : genshin.Client, uid : int) -> genshin.models.Notes:
		return await client.get_genshin_notes(uid)

	def execute(self, bot, messageData):
		client = asyncio.run(GetHoyoClient(messageData))
		if client is not None:
			genshinUID = asyncio.run(GetGameAccountUID(client, self.GENSHIN_GAME_NAME))
			if genshinUID is not None:
				try:
					userNotes : genshin.models.Notes = asyncio.run(self.GetGenshinNotes(client, genshinUID))

					if userNotes.remaining_transformer_recovery_time is not None:
						bot.send_message(messageData.channel, 
							f"{messageData.user}, {self.GENSHIN_EMOTE} Genshin data for {genshinUID} - Resin: {userNotes.current_resin}/{userNotes.max_resin} | Resin fully recovered in: {str(userNotes.remaining_resin_recovery_time)} | \
							Dailies: {('✅' if userNotes.claimed_commission_reward else '❌')} | Realm currency: {userNotes.current_realm_currency}/{userNotes.max_realm_currency} | \
							Parametric transformer {f'ready in {userNotes.remaining_transformer_recovery_time.days} day(s).' if userNotes.remaining_transformer_recovery_time.days > 0 else 'is ready!'}")
					else:
						bot.send_message(messageData.channel, 
							f"{messageData.user}, {self.GENSHIN_EMOTE} Genshin data for {genshinUID} - Resin: {userNotes.current_resin}/{userNotes.max_resin} | Resin fully recovered in: {str(userNotes.remaining_resin_recovery_time)} | \
							Dailies: {('✅' if userNotes.claimed_commission_reward else '❌')} | Realm currency: {userNotes.current_realm_currency}/{userNotes.max_realm_currency} | \
							Parametric transformer not yet obtained.")
				except genshin.errors.InternalDatabaseError:
					bot.send_message(messageData.channel, f"{messageData.user}, data doesn't exist! Please make sure your Real-time Notes and other settings are enabled in the HoyoLAB battle chronicle.")
					return
			else:
				bot.send_message(messageData.channel, f"{messageData.user} you do not have a Genshin Impact account. {self.GENSHIN_EMOTE}")
				return
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, you have not yet registered to use Hoyo commands or your cookies have expired/are unvalid! Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return

class HonkaiStarRailStaminaCheckCommand(Command):
	COMMAND_NAME = ["hsrstamina", "honkaistarrailstamina", "stamina"]
	COOLDOWN = 5
	DESCRIPTION = "Check your real-time remaining stamina! Requires HoyoLAB cookies to function. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md"

	STAR_RAIL_GAME_NAME = "hkrpg_global"
	STAR_RAIL_EMOTE = "🚄"

	async def GetStarRailNotes(self, client : genshin.Client, uid : int) -> genshin.models.StarRailNote:
		return await client.get_starrail_notes(uid)

	def execute(self, bot, messageData):
		client = asyncio.run(GetHoyoClient(messageData))
		if client is not None:
			starRailUID = asyncio.run(GetGameAccountUID(client, self.STAR_RAIL_GAME_NAME))
			if starRailUID is not None:
				userNotes : genshin.models.StarRailNote = asyncio.run(self.GetStarRailNotes(client, starRailUID))

				bot.send_message(messageData.channel, 
					f"{messageData.user}, {self.STAR_RAIL_EMOTE} Star Rail data for {starRailUID} - Stamina: {userNotes.current_stamina}/{userNotes.max_stamina} | Stamina fully recovered in: {str(userNotes.stamina_recover_time)} | \
					Reserve stamina: {userNotes.current_reserve_stamina} | Reserve stamina full: {'✅' if userNotes.is_reserve_stamina_full else '❌'} | Dailies: {'✅' if userNotes.current_train_score == userNotes.max_train_score else '❌'} ({userNotes.current_train_score}/{userNotes.max_train_score})")
			else:
				bot.send_message(messageData.channel, f"{messageData.user} you do not have a Honkai: Star Rail account. {self.STAR_RAIL_EMOTE}")
				return
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, you have not yet registered to use Hoyo commands or your cookies have expired/are unvalid! Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return

class ZenlessZoneZeroEnergyCheckCommand(Command):
	COMMAND_NAME = ["energy", "battery", "zzzenergy", "zenlesszonezeroenergy"]
	COOLDOWN = 5
	DESCRIPTION = "Check your real-time remaining energy! Requires HoyoLAB cookies to function. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md"

	ZZZ_GAME_NAME = "nap_global"
	ZZZ_EMOTE = "BangbooBounce"

	VIDEO_STORE_STATE = {genshin.models.VideoStoreState.REVENUE_AVAILABLE: "Revenue available!", genshin.models.VideoStoreState.WAITING_TO_OPEN: "Waiting to open.", genshin.models.VideoStoreState.CURRENTLY_OPEN: "Currently open."}

	async def GetZZZNotes(self, client : genshin.Client, uid : int) -> genshin.models.ZZZNotes:
		return await client.get_zzz_notes(uid)
	
	def execute(self, bot, messageData):
		client = asyncio.run(GetHoyoClient(messageData))
		if client is not None:
			zzzUID = asyncio.run(GetGameAccountUID(client, self.ZZZ_GAME_NAME))
			if zzzUID is not None:
				userNotes : genshin.models.ZZZNotes = asyncio.run(self.GetZZZNotes(client, zzzUID))

				bot.send_message(messageData.channel, 
					f"{messageData.user}, {self.ZZZ_EMOTE} Zenless Zone Zero data for {zzzUID} - Energy: {userNotes.battery_charge.current}/{userNotes.battery_charge.max} | Energy fully recovered in: {str(datetime.timedelta(seconds=userNotes.battery_charge.seconds_till_full))} | \
					Scratch card completed: {'✅' if userNotes.scratch_card_completed else '❌'} | Video store: {self.VIDEO_STORE_STATE[userNotes.video_store_state]} | Dailies: {'✅' if userNotes.engagement.current == userNotes.engagement.max else '❌'} ({userNotes.engagement.current}/{userNotes.engagement.max})")
			else:
				bot.send_message(messageData.channel, f"{messageData.user} you do not have a Zenless Zone Zero account. {self.ZZZ_EMOTE}")
				return
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, you have not yet registered to use Hoyo commands or your cookies have expired/are unvalid! Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
class HoyoGameDailyRewardClaimCommand(Command):
	COMMAND_NAME = ["hoyodaily", "hoyodailyreward", "hoyoreward", "hoyoclaim"]
	COOLDOWN = 5
	DESCRIPTION = "Claim HoyoLAB daily rewards on Genshin Impact, Honkai: Star Rail and Zenless Zone Zero!"

	GAME_NAME_TO_ENUM = {"genshin": genshin.Game.GENSHIN, "hsr": genshin.Game.STARRAIL, "zzz": genshin.Game.ZZZ}

	async def ClaimDailyRewards(self, client : genshin.Client, targetGame : genshin.Game) -> str:
		reward : genshin.models.DailyReward = await client.claim_daily_reward(game = targetGame)
		return f"{reward.name} x{reward.amount}"
	
	def execute(self, bot, messageData):
		client = asyncio.run(GetHoyoClient(messageData))
		if client is not None:
			try:
				args = messageData.content.split()
				targetGame = args[1]

				# Handle no game name
				if targetGame not in ["genshin", "hsr", "zzz", "all"]:
					bot.send_message(messageData.channel, f"{messageData.user}, invalid game name supplied! Valid game names are: genshin, hsr, zzz or all for to claim for all games at once.")
					return
				
				# Handle all games claim
				if targetGame == "all":
					resultStr = ""

					for game in ["genshin", "hsr", "zzz"]:
						try:
							claimResult = asyncio.run(self.ClaimDailyRewards(client, self.GAME_NAME_TO_ENUM[game]))
							resultStr += f"{game}: Claimed {claimResult}! "
						except genshin.AlreadyClaimed:
							resultStr += f"{game}: (already claimed) "
						except:
							resultStr += f"{game}: (no account) "

					bot.send_message(messageData.channel, f"{messageData.user}, {resultStr}")
				# Handle singular game claim				
				else:
					rewardData = asyncio.run(self.ClaimDailyRewards(client, self.GAME_NAME_TO_ENUM[targetGame]))
					bot.send_message(messageData.channel, f"{messageData.user}, successfully claimed {rewardData}!")
			except IndexError:
				bot.send_message(messageData.channel, f"{messageData.user}, you didn't supply a game name to claim daily rewards for! Valid games names are: genshin, hsr, zzz or all for to claim for all games at once.")
			except genshin.AlreadyClaimed:
				bot.send_message(messageData.channel, f"{messageData.user}, you already claimed daily rewards for that game today!")
			except:
				bot.send_message(messageData.channel, f"{messageData.user}, error - you probably don't have an account in that game.")
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, you have not yet registered to use Hoyo commands or your cookies have expired/are unvalid! Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
class HoyoDailyCheckReminderCommand(Command):
	COMMAND_NAME = "claimremind"
	COOLDOWN = 0
	DESCRIPTION = "Use this to remind everyone to use _hoyoclaim. Authorized user only."

	def execute(self, bot, messageData):
		# Check if the user is the authorized user or the broadcaster of the chat.
		if messageData.user == AUTHORIZED_USER or messageData.tags["user-id"] == messageData.tags["room-id"]:
			dbConnection = hoyoDBConnectionPool.get_connection()
			dbCursor = dbConnection.cursor()
			dbCursor.execute("SELECT username FROM hoyolabData")
			allUsers = dbCursor.fetchall()

			bot.send_message(messageData.channel, f"{', '.join([user[0] for user in allUsers])} time to use _hoyoclaim for daily rewards! HungryPaimon")

			dbConnection.close()
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, it's kind of you to be considerate, but only the bot owner or the broadcaster can use this command to avoid spam.")
		
class HoyoBannersCommand(Command):
	COMMAND_NAME = "hoyobanners"
	COOLDOWN = 5
	DESCRIPTION = "Check ongoing event banners for Hoyoverse games. Game name needs to be specified."

	async def GetEventBannerData(self, gameName: str) -> str:
		client = await GetKawaiibottoHoyoClient()
		response = ""
				
		if gameName == "genshin":
			genshinEvents : genshin.models.GenshinEventCalendar = await client.get_genshin_event_calendar(kawaiibottoGenshinUID)
			if len(genshinEvents.character_banners) > 0:
				response += f"Genshin Impact Version {genshinEvents.character_banners[0].version} Banners: "

			for characterBannerData in genshinEvents.character_banners:
				response += f"HungryPaimon {characterBannerData.name} - "
				for bannerCharacter in characterBannerData.characters:
					if bannerCharacter.rarity > 4:
						response += f"✨ {bannerCharacter.name} - "
				response += f"Ends in: {str(datetime.timedelta(seconds=int(characterBannerData.end_timestamp - time.time())))} "
			for weaponBannerData in genshinEvents.weapon_banners:
				weaponBannerCounter = 1

				response += f"HungryPaimon {weaponBannerData.name} - "
				for bannerWeapon in weaponBannerData.weapons:
					if bannerWeapon.rarity > 4:
						response += f"✨ {bannerWeapon.name} "
						weaponBannerCounter += 1
						if weaponBannerCounter == len(weaponBannerData.weapons):
							response += "- "
				response += f"Ends in: {str(datetime.timedelta(seconds=int(weaponBannerData.end_timestamp - time.time())))} "
		elif gameName == "hsr":
			hsrEvents : genshin.models.HSREventCalendar = await client.get_starrail_event_calendar(kawaiibottoStarRailUID)
			if len(hsrEvents.character_warps) > 0:
				response += f"Honkai: Star Rail Version {hsrEvents.character_warps[0].version} Banners: "

			charWarpCounter = 1
			lightConeWarpCounter = 1

			for characterWarpData in hsrEvents.character_warps:
				if charWarpCounter <= 1:
					response += f"🚆 Character Warps: "
				for warpCharacter in characterWarpData.characters:
					if warpCharacter.rarity > 4:
						response += f"✨ {warpCharacter.name} "

				charWarpCounter += 1
				if charWarpCounter == len(hsrEvents.character_warps):
					response += "- " 

				# Because just being able to remove the fraction would be too easy, Python datetime libraries hate conveniency :/
				endTimeDelta = characterWarpData.time_info.end - datetime.datetime.now(datetime.timezone.utc)
				endTimeDelta = datetime.timedelta(seconds=int(endTimeDelta.total_seconds()))
				response += f"Ends in: {str(endTimeDelta)} "
			for lightconeWarpData in hsrEvents.light_cone_warps:
				if lightConeWarpCounter <= 1:
					response += f"🚆 Light Cone Warps - "
				for warpLightCone in lightconeWarpData.light_cones:
					if warpLightCone.rarity > 4:
						response += f"✨ {warpLightCone.name} "

				lightConeWarpCounter += 1
				if lightConeWarpCounter == len(hsrEvents.light_cone_warps):
					response += "- " 

				# Because just being able to remove the fraction would be too easy, Python datetime libraries hate conveniency :/
				endTimeDelta = lightconeWarpData.time_info.end - datetime.datetime.now(datetime.timezone.utc)
				endTimeDelta = datetime.timedelta(seconds=int(endTimeDelta.total_seconds()))
				response += f"Ends in: {str(endTimeDelta)} "
		
		return response

	def execute(self, bot, messageData):
		args = messageData.content.split()
		targetGame = ""
		
		# Handle no game name
		try:
			targetGame = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"{messageData.user}, No game name supplied! Valid game names are: genshin, hsr")
			return

		# Handle invalid game name
		if targetGame not in ["genshin", "hsr"]:
			bot.send_message(messageData.channel, f"{messageData.user}, invalid game name supplied! Valid game names are: genshin, hsr")
			return
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, {asyncio.run(self.GetEventBannerData(targetGame))}")

class HoyoEventsComnand(Command):
	COMMAND_NAME = "hoyoevents"
	COOLDOWN = 5
	DESCRIPTION = "Check ongoing events for Hoyoverse games. Game name needs to be specified."

	async def GetEventData(self, gameName: str) -> str:
		client = await GetKawaiibottoHoyoClient()
		response = ""

		if gameName == "genshin":
			genshinEvents : genshin.models.GenshinEventCalendar = await client.get_genshin_event_calendar(kawaiibottoGenshinUID)
			if len(genshinEvents.character_banners) > 0:
				response += f"Genshin Impact v{genshinEvents.character_banners[0].version} events: "

			for genshinEvent in genshinEvents.events:
				if not genshinEvent.is_finished:
					if genshinEvent.end_time is not None:
						response += f"➡️  {genshinEvent.name} - Ends in: {str(datetime.timedelta(seconds=int(genshinEvent.end_timestamp - time.time())))} "
					else:
						response += f"⌛ {genshinEvent.name} - Not yet started "
		elif gameName == "hsr":
			hsrEvents : genshin.models.HSREventCalendar = await client.get_starrail_event_calendar(kawaiibottoStarRailUID)
			if len(hsrEvents.character_warps) > 0:
				response += f"HSR v{hsrEvents.character_warps[0].version} events: "

			for hsrEvent in hsrEvents.events:
				if hsrEvent.time_info is not None:
					# Ongoing event
					if hsrEvent.time_info.start < datetime.datetime.now(datetime.timezone.utc):
						response += f"➡️ {hsrEvent.name} - "
						# Because just being able to remove the fraction would be too easy, Python datetime libraries hate conveniency :/
						endTimeDelta = hsrEvent.time_info.end - datetime.datetime.now(datetime.timezone.utc)
						endTimeDelta = datetime.timedelta(seconds=int(endTimeDelta.total_seconds()))
						response += f"Ends in: {str(endTimeDelta)} "
					# Event not yet started
					else:
						response += f"⌛ {hsrEvent.name} - "
						# Because just being able to remove the fraction would be too easy, Python datetime libraries hate conveniency :/
						endTimeDelta = hsrEvent.time_info.start - datetime.datetime.now(datetime.timezone.utc)
						endTimeDelta = datetime.timedelta(seconds=int(endTimeDelta.total_seconds()))
						response += f"Starts in: {str(endTimeDelta)} "
				else:
					response += f"➡️ {hsrEvent.name} "

		return response

	def execute(self, bot, messageData):
		args = messageData.content.split()
		targetGame = ""
		
		# Handle no game name
		try:
			targetGame = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"{messageData.user}, No game name supplied! Valid game names are: genshin, hsr")
			return

		# Handle invalid game name
		if targetGame not in ["genshin", "hsr"]:
			bot.send_message(messageData.channel, f"{messageData.user}, invalid game name supplied! Valid game names are: genshin, hsr")
			return
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, {asyncio.run(self.GetEventData(targetGame))}")