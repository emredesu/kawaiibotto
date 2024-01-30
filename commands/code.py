from commands.command import Command
import inspect
import pathlib


class CodeCommand(Command):
	COMMAND_NAME = "code"
	COOLDOWN = 5
	DESCRIPTION = "Want to see the source code of a command? Use this command!"

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			searched_command = args[1]
		except IndexError:
			bot.send_message(messageData.channel, "Usage: _code (command name)")
		else:
			command_list = []

			for cmnd in bot.commands:
				if isinstance(cmnd.COMMAND_NAME, list):
					for alias in cmnd.COMMAND_NAME:
						command_list.append(alias)
				else:
					command_list.append(cmnd.COMMAND_NAME)

			if searched_command not in command_list:
				bot.send_message(messageData.channel, "There is no command with that name. :c")
				return
			else:
				command_object = None

				for cmnd in bot.commands:
					if isinstance(cmnd.COMMAND_NAME, list):
						for alias in cmnd.COMMAND_NAME:
							if alias == searched_command:
								command_object = cmnd
								break
					else:
						if cmnd.COMMAND_NAME == searched_command:
							command_object = cmnd
							break

			bot.send_message(messageData.channel, f"{messageData.user}, https://github.com/emredesu/kawaiibotto/blob/master/commands/{pathlib.Path(inspect.getfile(command_object.__class__)).stem}.py")
