from commands.command import Command


class HelpCommand(Command):
	COMMAND_NAME = "help"
	COOLDOWN = 5
	DESCRIPTION = "Don't quite understand what a command does? Use this for that command... like you did it for this command!"

	def execute(self, bot, messageData):
		try:
			command_to_get_help_for = messageData.content.split()[1]
		except IndexError:
			bot.send_message(messageData.channel, "Usage: _help {command name}")
		else:
			command_found = False

			for cmd in bot.commands:
				if isinstance(cmd.COMMAND_NAME, str) and cmd.COMMAND_NAME == command_to_get_help_for:
					bot.send_message(messageData.channel, messageData.user + ", " + cmd.DESCRIPTION)
					command_found = True
				elif isinstance(cmd.COMMAND_NAME, list):
					for commandName in cmd.COMMAND_NAME:
						if commandName == command_to_get_help_for:
							bot.send_message(messageData.channel, messageData.user + ", " + cmd.DESCRIPTION)
							command_found = True

			# If still not found, search whisper commands.
			if command_found is False:
				for cmd in bot.whisperCommands:
					if isinstance(cmd.COMMAND_NAME, str) and cmd.COMMAND_NAME == command_to_get_help_for:
						bot.send_message(messageData.channel, messageData.user + ", " + cmd.DESCRIPTION)
						command_found = True
					elif isinstance(cmd.COMMAND_NAME, list):
						for commandName in cmd.COMMAND_NAME:
							if commandName == command_to_get_help_for:
								bot.send_message(messageData.channel, messageData.user + ", " + cmd.DESCRIPTION)
								command_found = True

			if command_found is False:
				bot.send_message(messageData.channel, "Specified command was not found.")
				return
