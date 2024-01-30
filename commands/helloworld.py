from commands.command import Command


class HelloWorldCommand(Command):
	COMMAND_NAME = ["helloworld", "aliastest"]
	COOLDOWN = 5
	DESCRIPTION = "hello world, programmed to work and not to feel ;w;"

	def execute(self, bot, messageData):
		bot.send_message(messageData.channel, "hello! :DD")
