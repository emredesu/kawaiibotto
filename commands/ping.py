from commands.command import Command
import datetime


def calculate_uptime(bot):
	time_elapsed = (datetime.datetime.now() - bot.start_time)

	seconds = time_elapsed.seconds
	minutes = 0
	hours = 0
	days = time_elapsed.days

	if seconds >= 60:
		minutes += seconds // 60
		seconds = seconds % 60
	if minutes >= 60:
		hours += minutes // 60
		minutes = minutes % 60

	return "The bot has been running for {} {}, {} {}, {} {} and {} {}! ^w^".format(days, "days" if days > 1 or days == 0 else "day",
																					hours, "hours" if hours > 1 or hours == 0 else "hour",
																					minutes, "minutes" if minutes > 1 or minutes == 0 else "minute",
																					seconds, "seconds" if seconds > 1 or seconds == 0 else "second")


class PingCommand(Command):
	COMMAND_NAME = "ping"
	COOLDOWN = 3
	DESCRIPTION = "Check if the bot is running and get the bot's uptime."

	def execute(self, bot, user, message, channel):
		bot.send_message(channel, calculate_uptime(bot))
