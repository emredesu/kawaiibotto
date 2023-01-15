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
		except Exception as e:
			bot.send_message(channel, f"{user}, An error occured.")
			print(e)
			return
        
		
