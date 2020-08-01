from commands.command import Command
import requests


class RandomQuoteCommand(Command):
	COMMAND_NAME = "rq"
	COOLDOWN = 0
	DESCRIPTION = f"Get a random quote of yours or someone else's. Only usable for channels in https://logs.ivr.fi/channels. Example usage: _{COMMAND_NAME} emredesu forsen"

	def execute(self, bot, user, message, channel):
		args = message.split()

		try:
			person = args[1]
			ch = args[2]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (username) (channel)")
		else:
			try:
				channels_data = requests.get("https://logs.ivr.fi/channels").json()
			except requests.exceptions.ConnectionError:
				bot.send_message(channel, "ivr.fi API is down ;w;")
				return
			else:
				channels = [channels_data["channels"][i]["name"] for i in range(len(channels_data["channels"]))]

				if ch not in channels:
					bot.send_message(channel, "That channel is not logged by ivr.fi. Visit https://logs.ivr.fi/channels to see which channels are logged ^-^")
					return
				else:
					rq_data = requests.get(f"https://api.ivr.fi/logs/rq/{ch}/{person}").json()

					try:
						bot.send_message(channel, f"{rq_data['time24h']} #{ch} {rq_data['user']}: {rq_data['message']}")
					except KeyError:
						bot.send_message(channel, f"api.ivr.fi returned {rq_data['status']}: {rq_data['error']}")


class EmoteInfoCommand(Command):
	COMMAND_NAME = "emoteinfo"
	COOLDOWN = 5
	DESCRIPTION = f"Get info about an emote (whose emote is it, which tier is it etc.). Example usage: _{COMMAND_NAME} bepBlush"

	def execute(self, bot, user, message, channel):
		args = message.split()

		try:
			emote = args[1]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (emote)")
			return
		else:
			try:
				data = requests.get("https://api.ivr.fi/twitch/emotes/{}".format(emote)).json()

				ch = data["channel"]
				tier = data["tier"]
				emoteid = data["emoteid"]

				bot.send_message(channel, f"{emote} belongs to the channel {ch}, tier {tier} emote. https://twitchemotes.com/emotes/{emoteid}")
			except KeyError:
				error = requests.get(f"https://api.ivr.fi/twitch/emotes/{emote}").json()["error"]

				bot.send_message(channel, f"api.ivr.fi returned an error: {error}")

			except requests.exceptions.ConnectionError:
				bot.send_message(channel, "api.ivr.fi is down ;w;")
