from commands.command import Command


class HelloWorldCommand(Command):
	COMMAND_NAME = ["helloworld", "aliastest"]
	COOLDOWN = 5
	DESCRIPTION = "hello world, programmed to work and not to feel ;w;"

	def execute(self, bot, messageData):
		bot.send_reply_message(messageData, "hello! :DD")

class UpdateTestCommand(Command):
	COMMAND_NAME = "updatetest"

	def execute(self, bot, messageData):
		bot.send_reply_message(messageData, "update system implemented!")
