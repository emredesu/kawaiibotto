from commands.command import Command


class VanishCommand(Command):
	COMMAND_NAME = "vanish"
	COOLDOWN = 0
	DESCRIPTION = "poof"

	def execute(self, bot, user, message, channel):
		bot.send_message(channel, f"/timeout {user} 1")
