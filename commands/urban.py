from commands.command import Command
import requests


class UrbanCommand(Command):
	COMMAND_NAME = "urban"
	COOLDOWN = 5
	DESCRIPTION = "Get the most upvoted definition for a word in Urban Dictionary."

	def execute(self, bot, user, message, channel):
		api_url = "https://api.urbandictionary.com/v0/define"
		args = message.split()[1::]
		index = 0

		for arg in args:
			if arg.startswith("index:"):
				try:
					index = int(arg[6::])
				except ValueError:
					bot.send_message(channel, f"{user}, {arg[6::]} is not an integer :c")
					return

				args.remove(arg)

		if len(args) == 0:
			bot.send_message(channel, f"{user}, no argument supplied!")
			return

		query_params = {"term": " ".join(args)}
		data = requests.get(api_url, params=query_params).json()
		data["list"].sort(key=lambda x: int(int(x["thumbs_up"]) - int(x["thumbs_down"])), reverse=True)

		if not data["list"]:
			bot.send_message(channel, f"{user}, no results found.")
			return

		# f-strings can't have backslashes so we need to assign new line characters to variables.
		crlf = "\r\n"
		lf = "\n"

		try:
			currind_data = data["list"][index]

			definition = currind_data["definition"]
			example = currind_data["example"]
			
			replaced_characters = ["[", "]"]
			for char in replaced_characters:
				definition = definition.replace(char, "")
				example = example.replace(char, "")

			bot.send_message(channel, f"{user}, ({len(data['list'])} extra definitions) (+{currind_data['thumbs_up']}/-{currind_data['thumbs_down']}) {definition.replace(crlf, lf)} - Example: {example.replace(crlf, lf)}")
		except IndexError:
			bot.send_message(channel, f"{user}, Index too big! Max index for this query is {len(data['list']) - 1}.")
			return
