class Command:
	def __init__(self, commands):
		commands.append(self)

	COMMAND_NAME = ""
	COOLDOWN = 0
	DESCRIPTION = ""

	last_used = 0

	def execute(self, bot, user, message, channel):
		pass
