from commands.command import Command
from globals import OPENAI_APIKEY
import messagetypes
import openai
from typing import List, Dict
import time

class GPTMessageData:
	def __init__(self, isUserMessage: bool, messageContent: str, timestamp: int) -> None:
		self.userMessage = isUserMessage
		self.messageContent = messageContent
		self.timestamp = timestamp
		pass

class ChatBotCommand(Command):
	COMMAND_NAME = ["gpt", "chatgpt"]
	COOLDOWN = 5
	DESCRIPTION = "Talk to OpenAI's ChatGPT! Your messages sent through this command will be kept in the bot's memory for 5 minutes for use in continued \
					conversations with the bot. If you wish to erase the bot's memory of your messages and start fresh, append history:false to your message."
	
	# If this many seconds have passed since the user's last message data, their data will be wiped from the messageHistory dict.
	HISTORY_EXPIRE_AFTER = 300

	# This emoji will be put at the start of the bot response if the user is chatting with a history active.
	HISTORY_EMOJI = "⌛ "

	# key: username, value: message data related to that user (including the messages sent by the system)
	messageHistory: Dict[str, List[GPTMessageData]] = {}

	def __init__(self, commands):
		super().__init__(commands)
		openai.api_key = OPENAI_APIKEY

	def execute(self, bot, user, message, channel):
		maxTokens = 1000
		unhingedTag = "unhinged:true"
		historyWipeTag = "history:false"
		currentModel = "gpt-3.5-turbo"

		args = message.split()
		args.pop(0) # Get rid of the command invocation

		# "Unhinged" version, uses the oldest possible GPT model for some "unique" answers
		if unhingedTag in args:
			messagetypes.log("Swapped to unhinged version of GPT for the following instance of command invocation:")
			currentEngine = "text-davinci-001"
			args.pop(args.index(unhingedTag))

			try:
				completionResult = openai.Completion.create(engine=currentEngine, prompt=" ".join(args), max_tokens=maxTokens)
				bot.send_message(channel, f"{user}," + completionResult.choices[0].text)
				return
			except Exception as e:
				bot.send_message(channel, f"{user}, An error occured.")
				messagetypes.error(f"{e}")
				return
		elif historyWipeTag in args:
			args.pop(args.index(historyWipeTag))

			# Delete user history and start fresh with the new prompt			
			self.messageHistory.pop(user)

		userPrompt = " ".join(args)
		if not userPrompt:
			bot.send_message(channel, f"{user}, You haven't given the model a prompt! Example usage: _gpt Tell me a story about a turtle.")
			return
        
		try:
			userMessageHistory = []
			hasHistory = False

			# Check if the user has message history saved and that it's not timed out. If so, build the "messages" list.
			if user in self.messageHistory and (time.time() - self.messageHistory[user][-1].timestamp) < self.HISTORY_EXPIRE_AFTER:
				hasHistory = True

				for messageHistoryData in self.messageHistory[user]:
					# Message sent by a user
					if messageHistoryData.userMessage:
						userMessageHistory.append({"role": "user", "content": messageHistoryData.messageContent})
					# Message sent by the bot
					else:
						userMessageHistory.append({"role": "system", "content": messageHistoryData.messageContent})
			else:
				# If the user is still in message history despite not passing the previous condition check, that means their messages have expired, so we will wipe their history.
				if user in self.messageHistory:
					self.messageHistory.pop(user)

			# This new prompt is also added to the messages list.
			userMessageHistory.append({"role": "user", "content": userPrompt})

			# Save this new prompt to the user message history. If user does not exist in the history, create a new entry.
			if user in self.messageHistory:
				self.messageHistory[user].append(GPTMessageData(True, userPrompt, time.time()))
			else:
				self.messageHistory[user] = [GPTMessageData(True, userPrompt, time.time())]

			gptHTTPResponse = openai.ChatCompletion.create(model=currentModel, messages=userMessageHistory, max_tokens=maxTokens)
			generatedResponses = [choice.message["content"].strip() for choice in gptHTTPResponse["choices"]]

			chosenResponse = generatedResponses[0]
			bot.send_message(channel, f"{user}," + (self.HISTORY_EMOJI if hasHistory else " ") + chosenResponse)

			# Save bot response to message history too.
			self.messageHistory[user].append(GPTMessageData(False, chosenResponse, time.time()))
		except Exception as e:
			bot.send_message(channel, f"{user}, An error occured.")
			messagetypes.error(f"{e}")
			return

class ImageGenCommand(Command):
	COMMAND_NAME = ["dalle", "imagegen", "generateimage"]
	COOLDOWN = 5
	DESCRIPTION = "Create images using OpenAI's Dall-E!"

	def __init__(self, commands):
		super().__init__(commands)
		openai.api_key = OPENAI_APIKEY

	def execute(self, bot, user, message, channel):
		maxTokens = 1000

		args = message.split()
		args.pop(0)

		userPrompt = " ".join(args)
		if not userPrompt:
			bot.send_message(channel, f"{user}, You haven't given the model a prompt! Example usage: _dalle A cat playing with a mouse toy.")
			return
		
		try:
			bot.send_message(channel, f"{user}, Generating...")
			imageResult = openai.Image.create(prompt=userPrompt, n=1)
			bot.send_message(channel, f"{user}, {imageResult['data'][0]['url']}")
		except:
			bot.send_message(channel, f"{user}, An error occured.")
			return