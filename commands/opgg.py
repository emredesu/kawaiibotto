from commands.command import Command


class OpggCommand(Command):
	COMMAND_NAME = "opgg"
	COOLDOWN = 5
	DESCRIPTION = "Get OP.GG link of a user. Example usage: _opgg euw emredesu"

	def execute(self, bot, user, message, channel):
		args = message.split()

		available_regions = ["euw", "eune", "jp", "na", "oce", "br", "las", "lan", "ru", "tr", "sg", "id", "ph", "tw", "vn", "th", "kr"]

		try:
			region = args[1]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (optional region) (player)")
			return
		else:
			player_name = "+".join(args[2::])

			if region not in available_regions:
				bot.send_message(channel, f"Invalid region provided! Available regions are: {' '.join(available_regions)}")
			elif region == "kr":
				bot.send_message(channel, f"https://www.op.gg/summoner/userName={player_name}")
			else:
				bot.send_message(channel, f"https://{region}.op.gg/summoner/userName={player_name}")
