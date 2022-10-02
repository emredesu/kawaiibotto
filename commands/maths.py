from commands.command import Command
import requests
import urllib

class MathsCommand(Command):
	COMMAND_NAME = ["maths", "math", "eval"]
	COOLDOWN = 3
	DESCRIPTION = "Do maths!"

	def execute(self, bot, user, message, channel):
		args = message.split()
		args.pop(0)

		expression = "".join(args)
		expression = urllib.parse.quote(expression)

		if not expression:
			bot.send_message(channel, f"{user}, no expression was given!")
			return

		try:
			data = requests.get(f"http://api.mathjs.org/v4/?expr={expression}")
			bot.send_message(channel, data.text)
		except Exception as exception:
			bot.send_message(channel, f"Unidentified error occured: {exception.__class__.__name__}")
			return