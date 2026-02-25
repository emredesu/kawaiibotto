from commands.command import Command
import requests
import urllib

class MathsCommand(Command):
	COMMAND_NAME = ["maths", "math", "eval"]
	COOLDOWN = 3
	DESCRIPTION = "Do maths!"

	def execute(self, bot, messageData):
		args = messageData.content.split()
		args.pop(0)

		expression = "".join(args)
		expression = urllib.parse.quote(expression)

		if not expression:
			bot.send_reply_message(messageData, f"No expression was given!")
			return

		try:
			data = requests.get(f"http://api.mathjs.org/v4/?expr={expression}")
			bot.send_reply_message(messageData, str(float(data.text))) # Casting to float gets rid of Euler notation
		except Exception as exception:
			bot.send_reply_message(messageData, f"Unidentified error occured: {exception.__class__.__name__}")
			return