from commands.command import Command


class HelpCommand(Command):
	COMMAND_NAME = "help"
	COOLDOWN = 5
	DESCRIPTION = "Don't quite understand what a command does? Use this for that command... like you did it for this command!"

	def execute(self, bot, user, message, channel):
		try:
			command_to_get_help_for = message.split()[1]
		except IndexError:
			bot.send_message(channel, "Usage: _help {command name}")
		else:
			command_found = False

			for cmd in bot.commands:
				if isinstance(cmd.COMMAND_NAME, str) and cmd.COMMAND_NAME == command_to_get_help_for:
					bot.send_message(channel, cmd.DESCRIPTION)
					command_found = True
				elif isinstance(cmd.COMMAND_NAME, list):
					for commandName in cmd.COMMAND_NAME:
						if commandName == command_to_get_help_for:
							bot.send_message(channel, cmd.DESCRIPTION)
							command_found = True


			if command_found is False:
				bot.send_message(channel, "Specified command was not found.")
				return
