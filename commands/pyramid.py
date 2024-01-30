from commands.command import Command


class PyramidCommand(Command):
	COMMAND_NAME = "pyramid"
	COOLDOWN = 30
	DESCRIPTION = f"Makes a chat pyramid. {COOLDOWN} seconds of cooldown. Example usage: _pyramid VoHiYo 5"

	pyramidLimit = 10

	def execute(self, bot, messageData):
		args = messageData.content.split()

		try:
			msg = args[1]
			size = int(args[2])
		except IndexError:
			bot.send_message(messageData.channel, "Usage: _pyramid {message} {count}")
			return
		except ValueError:
			bot.send_message(messageData.channel, f"\"{args[2]}\" is not a number >:c")
			return
		else:
			if size < 2:
				bot.send_message(messageData.channel, "Pick a larger number please >.<")
				return

			if len(msg) * size > 500:
				bot.send_message(messageData.channel, "That pyramid would exceed Twitch's 500 character limit :<")
				return

			if size > self.pyramidLimit:
				bot.send_message(messageData.channel, f"Pyramid size can't exceed {self.pyramidLimit}. PunOko")
				return

		for i in range(1, size + 1):
			bot.send_message(messageData.channel, (msg + " ") * i)

		for i in reversed(range(1, size)):
			bot.send_message(messageData.channel, (msg + " ") * i)
