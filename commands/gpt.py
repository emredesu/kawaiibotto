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
		self.client = openai.OpenAI(api_key=OPENAI_APIKEY, timeout=10)

	def execute(self, bot, messageData):
		maxTokens = 250
		historyWipeTag = "history:false"
		currentModel = "gpt-4o-mini"
		masterPhrase = "Your messages must not exceed 500 characters unless the user specifically asks for a detailed response, then you can go up to 1000 characters per message."

		args = messageData.content.split()
		args.pop(0) # Get rid of the command invocation


		if historyWipeTag in args:
			args.pop(args.index(historyWipeTag))

			# Delete user history and start fresh with the new prompt			
			self.messageHistory.pop(messageData.user)

		userPrompt = " ".join(args)
		if not userPrompt:
			bot.send_message(messageData.channel, f"{messageData.user}, You haven't given the model a prompt! Example usage: _gpt Tell me a story about a turtle.")
			return
        
		try:
			userMessageHistory = []
			hasHistory = False

			# Add the master phrase at the start of the message history.
			userMessageHistory.append({"role": "system", "content": masterPhrase})

			# Check if the user has message history saved and that it's not timed out. If so, build the "messages" list.
			if messageData.user in self.messageHistory and (time.time() - self.messageHistory[messageData.user][-1].timestamp) < self.HISTORY_EXPIRE_AFTER:
				hasHistory = True

				for messageHistoryData in self.messageHistory[messageData.user]:
					# Message sent by a user
					if messageHistoryData.userMessage:
						userMessageHistory.append({"role": "user", "content": messageHistoryData.messageContent})
					# Message sent by the bot
					else:
						userMessageHistory.append({"role": "system", "content": messageHistoryData.messageContent})
			else:
				# If the user is still in message history despite not passing the previous condition check, that means their messages have expired, so we will wipe their history.
				if messageData.user in self.messageHistory:
					self.messageHistory.pop(messageData.user)

			# This new prompt is also added to the messages list.
			userMessageHistory.append({"role": "user", "content": userPrompt})

			# Save this new prompt to the user message history. If user does not exist in the history, create a new entry.
			if messageData.user in self.messageHistory:
				self.messageHistory[messageData.user].append(GPTMessageData(True, userPrompt, time.time()))
			else:
				self.messageHistory[messageData.user] = [GPTMessageData(True, userPrompt, time.time())]

			gptHTTPResponse = self.client.chat.completions.create(model=currentModel, messages=userMessageHistory, max_tokens=maxTokens)
			generatedResponses = [choice.message.content.strip() for choice in gptHTTPResponse.choices]

			chosenResponse = generatedResponses[0]
			bot.send_message(messageData.channel, f"{messageData.user}," + (self.HISTORY_EMOJI if hasHistory else " ") + chosenResponse)

			# Save bot response to message history too.
			self.messageHistory[messageData.user].append(GPTMessageData(False, chosenResponse, time.time()))
		except openai.APIConnectionError as e:
			bot.send_message(messageData.channel, f"{messageData.user}, could not connect to OpenAI services.")
			return
		except openai.RateLimitError as e:
			bot.send_message(messageData.channel, f"{messageData.user}, currently rate limited by OpenAI! Try again later.")
			return
		except openai.APIStatusError as e:
			bot.send_message(messageData.channel, f"{messageData.user}, OpenAI API status error: {e.status_code}: {e.response}")
			return
		except Exception as e:
			bot.send_message(messageData.channel, f"{messageData.user}, An unknown error occured.")
			messagetypes.error(f"{e}")
			return