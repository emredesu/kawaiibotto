from commands.command import Command
from messagetypes import error
import requests
import re
from datetime import datetime, timezone
import dateutil.parser 


class RandomQuoteCommand(Command):
	COMMAND_NAME = "rq"
	COOLDOWN = 0
	DESCRIPTION = f"Get a random quote of yours or someone else's. Only usable for channels in https://logs.ivr.fi/channels. Example usage: _{COMMAND_NAME} emredesu forsen"

	def __init__(self, commands):
		super().__init__(commands)
		try:
			channels_data = requests.get("https://logs.ivr.fi/channels").json()
		except:
			error("can't import RandomQuoteCommand, ivr.fi API is down ;w;")
			return
		else:
			self.channels = [channels_data["channels"][i]["name"] for i in range(len(channels_data["channels"]))]

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			person = args[1].replace("@", "")
			ch = args[2]
		except IndexError:
			bot.send_message(messageData.channel, f"Usage: _{self.COMMAND_NAME} (username) (channel)")
		else:
			if ch not in self.channels:
				bot.send_message(messageData.channel, "That channel is not logged by the API. Visit https://logs.ivr.fi/channels to see which channels are logged ^-^")
				return
			else:
				request = requests.get(f"https://logs.ivr.fi/channel/{ch}/user/{person}/random?json=1")
				
				if request.status_code != 200:
					bot.send_message(messageData.channel, f"{messageData.user}, API returned {request.status_code}.")
					return

				rq_data = request.json()["messages"][0]			

				try:
					timestamp = rq_data["timestamp"]
					datetimeObj = dateutil.parser.parse(timestamp).replace(tzinfo=None)
					deltaTime = datetime.now() - datetimeObj

					dayDifferential = deltaTime.days

					bot.send_message(messageData.channel, f"{dayDifferential} days ago, #{rq_data['channel']} {rq_data['username']}: {rq_data['text']}")
				except KeyError:
					bot.send_message(messageData.channel, f"{messageData.user}, API error.")
					return


class EmoteInfoCommand(Command):
	COMMAND_NAME = ["emoteinfo", "weit"]
	COOLDOWN = 5
	DESCRIPTION = f"Get info about an emote (whose emote is it, which tier is it etc.). Example usage: _{COMMAND_NAME} bepBlush"

	def execute(self, bot, messageData):
		args = messageData.content.split()
		data = None

		try:
			emote = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"Usage: _{self.COMMAND_NAME} (emote name or emote ID)")
			return
		else:
			try:
				rawData = requests.get("https://api.ivr.fi/v2/twitch/emotes/{}".format(emote))
				if rawData.status_code != 200:
					raise KeyError # Intentionally raise a key error to try for an ID.

				data = rawData.json()

				ch = data["channelLogin"]

				bot.send_message(messageData.channel, f"{emote} belongs to channel \"{ch}\". https://emotes.awoo.nl/twitch/{ch}")
			except KeyError:
				# On failure, try again with the ?id=true parameter in case the given param is an emote code.
				try:
					rawData = requests.get("https://api.ivr.fi/v2/twitch/emotes/{}?id=true".format(emote))
					data = rawData.json()

					if rawData.status_code != 200:
						raise KeyError
					
					ch = data["channelLogin"]
					emoteName = data["emoteCode"]

					bot.send_message(messageData.channel, f"{emoteName} belongs to channel \"{ch}\". https://emotes.awoo.nl/twitch/{ch}")
				except KeyError:
					# Lastly, try to extract the emote code from the given string in case it's an emote URL.
					emoteCode = ""
					try:
						emoteCode = re.findall("v2/(.*)/default", emote)[0]

						rawData = requests.get("https://api.ivr.fi/v2/twitch/emotes/{}?id=true".format(emoteCode))
						data = rawData.json()
						
						ch = data["channelLogin"]
						emoteName = data["emoteCode"]

						bot.send_message(messageData.channel, f"{emoteName} belongs to channel \"{ch}\". https://chatvau.lt/channel/twitch/{ch}")
					except (IndexError, KeyError):
						# Give up.
						statusCode = data["statusCode"]
						errorMessage = data["error"]["message"]

						bot.send_message(messageData.channel, f"API returned {statusCode}: {errorMessage}. If you're certain that this is a valid emote, try using the command with the emote code.")

			except requests.exceptions.ConnectionError:
				bot.send_message(messageData.channel, "API is down ;w;")
