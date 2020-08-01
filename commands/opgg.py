from commands.command import Command


class OpggCommand(Command):
	COMMAND_NAME = "opgg"
	COOLDOWN = 5
	DESCRIPTION = "Get OP.GG link of a user. KR server is assumed by op.gg if no regional info is provided. Example usage: _opgg na BUZZLIGHTYEAR99 / _opgg hide on bush (korea)"

	def execute(self, bot, user, message, channel):
		args = message.split()

		available_regions = ["euw", "eune", "jp", "na", "oce", "br", "las", "lan", "ru", "tr", "sg", "id", "ph", "tw", "vn", "th"]

		try:
			region = args[1]
		except IndexError:
			bot.send_message(channel, f"Usage: _{self.COMMAND_NAME} (optional region) (player)")
			return
		else:
			if region not in available_regions:
				player_name = "+".join(args[1::])

				bot.send_message(channel, f"https://www.op.gg/summoner/userName={player_name}")
			else:
				player_name = "+".join(args[2::])

				bot.send_message(channel, f"https://{region}.op.gg/summoner/userName={player_name}")
