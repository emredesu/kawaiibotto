from commands.command import Command
from globals import WOLFRAM_APP_ID
import wolframalpha


class QueryCommand(Command):
	COMMAND_NAME = "query"
	COOLDOWN = 3
	DESCRIPTION = "Ask Wolfram-Alpha a question! Make sure you're as clear as possible. Example usage: _query Convert 1 euro to Turkish liras"

	def execute(self, bot, user, message, channel):
		client = wolframalpha.Client(WOLFRAM_APP_ID)
		question = message[6::]

		result = client.query(question)

		if result["@success"] == "false":
			bot.send_message(channel, f"{user}, Wolfram-Alpha did not understand your question ;w;")
			return
		else:
			try:
				result_text = next(result.results).text.replace("\n", " ")
				bot.send_message(channel, f"/me Query result: {result_text}")
			except StopIteration:
				bot.send_message(channel, f"{user}, No proper answer was found for your query ;w;")
