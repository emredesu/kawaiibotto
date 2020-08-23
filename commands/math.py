from commands.command import Command
from numexpr import evaluate


class MathCommand(Command):
	COMMAND_NAME = ["math", "calculate", "eval", "evaluate"]
	COOLDOWN = 5
	DESCRIPTION = "Do maths! To use special functions, for example square root, use sqrt(number)."

	def execute(self, bot, user, message, channel):
		try:
			args = message.split()
			expression = message[len(args[0]) + 1::]
		except IndexError:
			bot.send_message(channel, "Usage example: _math 1 + 1")
		else:
			try:
				bot.send_message(channel, str(evaluate(expression)))
			except Exception as e:
				bot.send_message(channel, str(e.__class__.__name__) + ": " + str(e))
