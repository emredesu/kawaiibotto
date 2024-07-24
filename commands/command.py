class Command:
	def __init__(self, commands):
		commands.append(self)

	COMMAND_NAME = ""
	COOLDOWN = 0
	DESCRIPTION = ""

	lastUseTimePerUser = {}

	def execute(self, bot, messageData):
		pass

class WhisperComand:
	def __init__(self, commands):
		commands.append(self)

		COMMAND_NAME = ""
		COOLDOWN = 0
		DESCRIPTION = ""

		lastUseTimePerUser = {}

	def execute(self, bot, messageData):
		pass