import re

# A class that handles the parsing of Twitch IRC messages.
class TwitchIRCMessage:
	messageType: str = None
	hasTags: bool = False
	tags: dict = {}

	# PRIVMSG data
	user: str = None
	channel: str = None
	content: str = None

	def __init__(self, message: str):
		#print(f"Now parsing: {message} \n")

		if message[0] == "@": # This message contains tags. Tags will be parsed and placed into the "tags" dict.
			self.hasTags = True
			
			# Seperate tag data and IRC message data
			messageArgs = message.split(" ", 1)

			#Parse tags
			self.ParseTags(messageArgs[0])
			
			# Parse IRC message
			self.ParseIRCMessage(messageArgs[1])
		elif message[0] == ":": # This is an IRC message.
			self.ParseIRCMessage(message)
		else: # This message is probably a PING message. Otherwise we don't know what it is so we will not handle it.
			if message == "PING :tmi.twitch.tv":
				self.messageType = "PING"

		#print(f"---Extracted message data---\nmessageType: {self.messageType} user: {self.user} channel: {self.channel} content: {self.content} tagCount: {len(self.tags)} tags: {self.tags}\n")

	# Parse all tags and prepare the "tags" dict.
	def ParseTags(self, tags: str) -> None:
		tagData = tags.split(";")
		for tag in tagData:
			tagArgs = tag.split("=")
			self.tags[tagArgs[0]] = tagArgs[1]

	# Parse IRC message, set messageType based on the data and process it further if it's a PRIVMSG.
	def ParseIRCMessage(self, message: str) -> None:
		#print(f"\nPARSING IRC MESSAGE: {message}")
		messageArgs = message.split(" ")
		self.messageType = messageArgs[1]
		
		# If message type is a PRIVMSG, extract the data from it.
		if messageArgs[1] == "PRIVMSG":
			self.ParsePRIVMSG(message)

	# Extract username, channel and message content from PRIVMSG.
	def ParsePRIVMSG(self, message: str) -> None:
		messageArgs = message.split(" ", 3)
		self.user = re.search("(?<=:)(.*?)(?=!)", messageArgs[0]).group(0)
		self.channel = messageArgs[2].removeprefix("#").removesuffix(":")
		self.content = messageArgs[3].removeprefix(":")