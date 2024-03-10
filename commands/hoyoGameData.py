from commands.command import Command
from globals import GENSHIN_MYSQL_DB_HOST, GENSHIN_MYSQL_DB_USERNAME, GENSHIN_MYSQL_DB_PASSWORD, GENSHIN_DB_POOL_SIZE
import mysql.connector
import mysql.connector.pooling
from messagetypes import error, log
import traceback
import genshin
import asyncio
import datetime

hoyoDBConnectionPool = mysql.connector.pooling.MySQLConnectionPool(host=GENSHIN_MYSQL_DB_HOST, user=GENSHIN_MYSQL_DB_USERNAME, password=GENSHIN_MYSQL_DB_PASSWORD, database="hoyolabData", pool_size=GENSHIN_DB_POOL_SIZE)

class GenshinResinCheckCommand(Command):
	COMMAND_NAME = ["genshinresin", "resin", "resincheck"]
	COOLDOWN = 5
	DESCRIPTION = "Check your real-time remaining resin! Requires HoyoLAB cookies to function. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md"

	async def GetUserNotes(self, ltuid, ltoken, uid):
		cookies = {"ltuid":ltuid, "ltoken":ltoken}
		client = genshin.Client(cookies)
		userNotes = await client.get_notes(uid)
		return userNotes

	def execute(self, bot, messageData):
		args = messageData.content.split()
		args.pop(0)

		dbConnection = hoyoDBConnectionPool.get_connection()
		dbCursor = dbConnection.cursor()

		if len(args) > 0 and args[0] == "register":
			ltuid = ""
			ltoken = ""
			genshinUID = ""
			hsrUID = ""

			for arg in args:
				if arg.startswith("ltuid:"):
					ltuid = arg[6::]
				elif arg.startswith("ltoken:"):
					ltoken = arg[7::]
				elif arg.startswith("genshinuid:"):
					genshinUID = arg[11::]
				elif arg.startswith("hsruid:"):
					hsrUID = arg[7::]

			if ltuid == "" or ltoken == "" or genshinUID == "":
				bot.send_message(messageData.channel, f"{messageData.user}, Invalid registration structure. Should be as follows: _resin register ltuid:(ltuid) ltoken:(ltoken) genshinuid:(uid). Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
				return
			
			dbCursor.execute("INSERT INTO hoyolabData VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ltuid=VALUES(ltuid), ltoken=VALUES(ltoken), genshinUID=VALUES(genshinUID)", (int(messageData.tags["user-id"]), messageData.user, genshinUID, hsrUID, ltuid, ltoken))
			dbConnection.commit()

			bot.send_message(messageData.channel, f"{messageData.user}, successfully registered your HoyoLAB cookies. You may now use the command without any params to retrieve your Genshin Impact in-game data.")
			return
		elif len(args) > 0 and args[0] == "help":
			bot.send_message(messageData.channel, f"{messageData.user}, Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return

		dbCursor.execute("SELECT ltuid, ltoken, genshinUID FROM hoyolabData WHERE userID=%s", (int(messageData.tags["user-id"]),))
		result = dbCursor.fetchone()

		ltuid = ""
		ltoken = ""
		genshinUID = ""
		try:
			ltuid = result[0]
			ltoken = result[1]
			genshinUID = result[2]
		except:
			bot.send_message(messageData.channel, f"{messageData.user} database error! Did you register using _resin register ltuid:(ltuid) ltoken:(ltoken) genshinuid:(uid)? Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
		try:
			userNotes = asyncio.run(self.GetUserNotes(ltuid, ltoken, genshinUID))
			bot.send_message(messageData.channel, 
					f"{messageData.user}, Genshin data for {genshinUID} - Resin: {userNotes.current_resin}/{userNotes.max_resin} | Resin fully recovered in: {str(userNotes.remaining_resin_recovery_time)} | \
					Dailies: {('Completed' if userNotes.claimed_commission_reward else 'Not yet completed')} | Realm currency: {userNotes.current_realm_currency}/{userNotes.max_realm_currency}")
		except:
			bot.send_message(messageData.channel, f"{messageData.user}, failed to fetch data. The data you provided while registering is probably faulty/expired. Please try registering using _resin register ltuid:(ltuid) ltoken:(ltoken) genshinuid:(uid) again. If you JUST registered, please try again in a minute.")
		finally:
			dbConnection.close()


class HonkaiStarRailStaminaCheckCommand(Command):
	COMMAND_NAME = ["hsrstamina", "honkaistarrailstamina", "stamina"]
	COOLDOWN = 5
	DESCRIPTION = "Check your real-time remaining stamina! Requires HoyoLAB cookies to function. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md"

	async def GetHSRUserNotes(self, ltuid, ltoken, uid):
		cookies = {"ltuid":ltuid, "ltoken":ltoken}
		client = genshin.Client(cookies)
		userNotes = await client.get_starrail_notes(uid)
		return userNotes

	def execute(self, bot, messageData):
		args = messageData.content.split()
		args.pop(0)

		dbConnection = hoyoDBConnectionPool.get_connection()
		dbCursor = dbConnection.cursor()

		if len(args) > 0 and args[0] == "register":
			ltuid = ""
			ltoken = ""
			genshinUID = ""
			hsrUID = ""

			for arg in args:
				if arg.startswith("ltuid:"):
					ltuid = arg[6::]
				elif arg.startswith("ltoken:"):
					ltoken = arg[7::]
				elif arg.startswith("genshinuid:"):
					genshinUID = arg[11::]
				elif arg.startswith("hsruid:"):
					hsrUID = arg[7::]

			if ltuid == "" or ltoken == "" or hsrUID == "":
				bot.send_message(messageData.channel, f"{messageData.user}, Invalid registration structure. Should be as follows: _stamina register ltuid:(ltuid) ltoken:(ltoken) hsruid:(uid). Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
				return
			
			dbCursor.execute("INSERT INTO hoyolabData VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE ltuid=VALUES(ltuid), ltoken=VALUES(ltoken), hsrUID=VALUES(hsrUID)", (int(messageData.tags["user-id"]), messageData.user, genshinUID, hsrUID, ltuid, ltoken))
			dbConnection.commit()

			bot.send_message(messageData.channel, f"{messageData.user}, successfully registered your HoyoLAB cookies. You may now use the command without any params to retrieve your Honkai: Star Rail in-game data.")
			return
		elif len(args) > 0 and args[0] == "help":
			bot.send_message(messageData.channel, f"{messageData.user}, Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
		dbCursor.execute("SELECT ltuid, ltoken, hsrUID FROM hoyolabData WHERE userID=%s", (int(messageData.tags["user-id"]),))
		result = dbCursor.fetchone()

		ltuid = ""
		ltoken = ""
		hsrUID = ""
		try:
			ltuid = result[0]
			ltoken = result[1]
			hsrUID = result[2]
		except:
			bot.send_message(messageData.channel, f"{messageData.user} database error! Did you register using _stamina register ltuid:(ltuid) ltoken:(ltoken) hsruid:(uid)? Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
			return
		
		try:
			userNotes = asyncio.run(self.GetHSRUserNotes(ltuid, ltoken, hsrUID))
			bot.send_message(messageData.channel, 
					f"{messageData.user}, HSR data for {hsrUID} - Stamina: {userNotes.current_stamina}/{userNotes.max_stamina} | Stamina fully recovered in: {str(userNotes.stamina_recover_time)}")
		except:
			bot.send_message(messageData.channel, f"{messageData.user}, failed to fetch data. You might be missing the required data for this type of query, or the data you provided while registering is faulty. Please try registering using  _stamina register ltuid:(ltuid) ltoken:(ltoken) hsruid:(uid) again. If you JUST registered, please try again in a minute. Registration tutorial: https://github.com/emredesu/kawaiibotto/blob/master/how_to_register_for_hoyo_game_data_check.md")
		finally:
			dbConnection.close()
