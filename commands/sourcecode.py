from commands.command import Command


class SourceCodeCommand(Command):
	COMMAND_NAME = ["sourcecode", "github"]
	COOLDOWN = 5
	DESCRIPTION = "Get the Github link to spagetti! 🍝 "

	def execute(self, bot, messageData):
		bot.send_message(messageData.channel, "https://github.com/emredesu/kawaiibotto")
