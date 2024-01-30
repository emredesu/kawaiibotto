from commands.command import Command
from globals import WOLFRAM_APP_ID
import wolframalpha


class QueryCommand(Command):
	COMMAND_NAME = "query"
	COOLDOWN = 3
	DESCRIPTION = "Ask Wolfram-Alpha a question! Make sure your question is as clear and concise as possible. Example usage: _query Convert 1 Euro to Turkish liras"

	def execute(self, bot, messageData):
		client = wolframalpha.Client(WOLFRAM_APP_ID)
		question = messageData.content[6::]

		result = client.query(question)

		if result["@success"] == "false":
			bot.send_message(messageData.channel, f"{messageData.user}, Wolfram-Alpha did not understand your question.")
			return
		else:
			try:
				result_text = next(result.results).text.replace("\n", " ")
				bot.send_message(messageData.channel, f"/me Query result: {result_text}")
			except StopIteration:
				bot.send_message(messageData.channel, f"{messageData.user}, No proper answer was found for your query.")
