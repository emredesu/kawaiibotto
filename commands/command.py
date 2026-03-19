class Command:
	def __init__(self, commands):
		self.lastUseTimePerUser = {}
		commands.append(self)

	COMMAND_NAME = ""
	COOLDOWN = 0
	DESCRIPTION = ""


	def execute(self, bot, messageData):
		pass

class WhisperComand:
	def __init__(self, commands):
		self.lastUseTimePerUser = {}
		commands.append(self)

	COMMAND_NAME = ""
	COOLDOWN = 0
	DESCRIPTION = ""


	def execute(self, bot, messageData):
		pass

# This command type can be triggered through various conditions (e.g. keywords, random chance etc.). This command type also only
# handles messages received on pre-determined channels.
class CustomCommand:
	def __init__(self, commands):
		commands.append(self)

	CHANNELS = []

	def HandleMessage(self, bot, messageData):
		pass