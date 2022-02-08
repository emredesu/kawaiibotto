from commands.command import Command
from messagetypes import error
import requests


class RandomQuoteCommand(Command):
	COMMAND_NAME = "rq"
	COOLDOWN = 0
	DESCRIPTION = f"Get a random quote of yours or someone else's. Only usable for channels in https://logs.ivr.fi/channels. Example usage: _{COMMAND_NAME} emredesu forsen"

	def __init__(self, commands):
		super().__init__(commands)
		try:
			channels_data = requests.get("https://logs.ivr.fi/channels").json()
		except requests.exceptions.ConnectionError:
			error("can't import RandomQuoteCommand, ivr.fi API is down ;w;")
			return
		else:
			self.channels = [channels_data["channels"][i]["name"] for i in range(len(channels_data["channels"]))]

	def execute(self, bot, user, message, channel):
		args = message.split()

		try:
			person = args[1]
			ch = args[2]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (username) (channel)")
		else:
			if ch not in self.channels:
				bot.send_message(channel, "That channel is not logged by the API. Visit https://logs.ivr.fi/channels to see which channels are logged ^-^")
				return
			else:
				rq_data = requests.get(f"https://api.ivr.fi/logs/rq/{ch}/{person}").json()

				try:
					bot.send_message(channel, f"{rq_data['time']} ago, #{ch} {rq_data['user']}: {rq_data['message']}")
				except KeyError:
					bot.send_message(channel, f"API returned {rq_data['status']}: {rq_data['error']}")


class EmoteInfoCommand(Command):
	COMMAND_NAME = ["emoteinfo", "weit"]
	COOLDOWN = 5
	DESCRIPTION = f"Get info about an emote (whose emote is it, which tier is it etc.). Example usage: _{COMMAND_NAME} bepBlush"

	def execute(self, bot, user, message, channel):
		args = message.split()
		data = None

		try:
			emote = args[1]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (emote name or emote ID)")
			return
		else:
			try:
				data = requests.get("https://api.ivr.fi/v2/twitch/emotes/{}".format(emote)).json()

				ch = data["channelLogin"]

				bot.send_message(channel, f"{emote} belongs to channel \"{ch}\". https://emotes.raccatta.cc/twitch/{ch}")
			except KeyError:
				# On failure, try again with the ?id=true parameter in case the given param is an emote code.
				try:
					data = requests.get("https://api.ivr.fi/v2/twitch/emotes/{}?id=true".format(emote)).json()
					
					ch = data["channelLogin"]
					emoteName = data["emoteCode"]

					bot.send_message(channel, f"{emoteName} belongs to channel \"{ch}\". https://emotes.raccatta.cc/twitch/{ch}")
				except KeyError:
					# Give up if that fails too.
					statusCode = data["statusCode"]
					errorMessage = data["message"]

					bot.send_message(channel, f"API returned {statusCode}: {errorMessage}. If you're certain that this is a valid emote, try using the command with the emote code.")

			except requests.exceptions.ConnectionError:
				bot.send_message(channel, "API is down ;w;")
