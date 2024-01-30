from commands.command import Command


class VanishCommand(Command):
	COMMAND_NAME = "vanish"
	COOLDOWN = 0
	DESCRIPTION = "poof"

	def execute(self, bot, messageData):
		bot.send_message(messageData.channel, f"/timeout {messageData.user} 1")
