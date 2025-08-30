from commands.command import Command
from globals import TWITCH_API_HEADERS
import requests


class UserIDCommand(Command):
	COMMAND_NAME = ["uid", "userid"]
	COOLDOWN = 0
	DESCRIPTION = f"Gets you the Twitch userID of a person. Example usage: _{COMMAND_NAME} kawaiibotto"

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			username = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"Usage: _{self.COMMAND_NAME} (username)")
			return
		else:
			url = f"https://api.twitch.tv/helix/users?login={username}"
			data = requests.get(url, headers=TWITCH_API_HEADERS).json()

			try:
				print(data)
				userid = data["data"][0]["id"]
			except IndexError:
				bot.send_message(messageData.channel, "User not found ¯\_(ツ)_/¯")
			else:
				bot.send_message(messageData.channel, userid)


class ProfilePictureCommand(Command):
	COMMAND_NAME = ["profilepic", "profilepicture", "pfp"]
	COOLDOWN = 0
	DESCRIPTION = "Get a link to a user's profile picture."

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			username = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"Usage: _{self.COMMAND_NAME} (username)")
			return
		else:
			url = f"https://api.twitch.tv/helix/users?login={username}"
			data = requests.get(url, headers=TWITCH_API_HEADERS).json()

			try:
				userid = data["data"][0]["profile_image_url"]
			except IndexError:
				bot.send_message(messageData.channel, "User not found ¯\_(ツ)_/¯")
			else:
				bot.send_message(messageData.channel, userid)


class EmotesCommand(Command):
	COMMAND_NAME = "emotes"
	COOLDOWN = 5
	DESCRIPTION = "Get a twitchemotes.com link of a user. Example usage: _emotes Verniy"

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			username = args[1]
		except IndexError:
			bot.send_message(messageData.channel, f"Usage: _{self.COMMAND_NAME} (username)")
			return
		else:
			url = f"https://api.twitch.tv/helix/users?login={username}"
			data = requests.get(url, headers=TWITCH_API_HEADERS).json()

			try:
				userid = data["data"][0]["id"]
			except IndexError:
				bot.send_message(messageData.channel, "User not found ¯\_(ツ)_/¯")
				return
			else:
				broadcaster_type = data["data"][0]["broadcaster_type"]

				if broadcaster_type not in ["partner", "affiliate"]:
					bot.send_message(messageData.channel, "That user is not an affiliate nor a partner. ;w;")
					return
				else:
					bot.send_message(messageData.channel, "https://chatvau.lt/channel/twitch/{}".format(username))
