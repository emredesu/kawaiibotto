from commands.command import Command


class HelloWorldCommand(Command):
	COMMAND_NAME = "helloworld"
	COOLDOWN = 5
	DESCRIPTION = "hello world, programmed to work and not to feel ;w;"

	def execute(self, bot, user, message, channel):
		bot.send_message(channel, "hello! :DD")
