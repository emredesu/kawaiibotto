from commands.command import Command
from globals import OPENAI_APIKEY
import openai

class ChatBotCommand(Command):
	COMMAND_NAME = ["gpt", "chatbot", "openai"]
	COOLDOWN = 5
	DESCRIPTION = "Talk to OpenAI's GPT-3!"

	def __init__(self, commands):
		super().__init__(commands)
		openai.api_key = OPENAI_APIKEY

	def execute(self, bot, user, message, channel):
		maxTokens = 1000

		args = message.split()
		args.pop(0)

		userPrompt = " ".join(args)
		if not userPrompt:
			bot.send_message(channel, f"{user}, You haven't given the model a prompt! Example usage: _gpt Tell me a story about a turtle.")
			return
        
		try:
			completionResult = openai.Completion.create(engine="text-davinci-001", prompt=userPrompt, max_tokens=maxTokens)
			bot.send_message(channel, f"{user}," + completionResult.choices[0].text)
		except:
			bot.send_message(channel, f"{user}, An error occured.")
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
		
