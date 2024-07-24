from commands.command import Command


class CommandsCommand(Command):
	COMMAND_NAME = "commands"
	COOLDOWN = 5
	DESCRIPTION = "Get a list of currently available commands."

	def execute(self, bot, messageData):
		command_list = []

		for cmd in bot.commands:
			if isinstance(cmd.COMMAND_NAME, list):
				for alias in cmd.COMMAND_NAME:
					command_list.append(alias)
			else:
				command_list.append(cmd.COMMAND_NAME)

		for cmd in bot.whisperCommands:
			if isinstance(cmd.COMMAND_NAME, list):
				for alias in cmd.COMMAND_NAME:
					command_list.append("(w)" + alias)
			else:
				command_list.append("(w)" + cmd.COMMAND_NAME)

		bot.send_message(messageData.channel, f"Currently available commands are: {' '.join(command_list)}")
