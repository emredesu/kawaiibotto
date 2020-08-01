from commands.helloworld import HelloWorldCommand
from commands.pyramid import PyramidCommand
from commands.ivrfi_api_commands import RandomQuoteCommand, EmoteInfoCommand
from commands.opgg import OpggCommand
from commands.twitch_api_commands import UserIDCommand, EmotesCommand
from commands.query import QueryCommand
from commands.ping import PingCommand


def instantiate_commands(commands):
	HelloWorldCommand(commands)
	PyramidCommand(commands)
	RandomQuoteCommand(commands)
	EmoteInfoCommand(commands)
	OpggCommand(commands)
	UserIDCommand(commands)
	EmotesCommand(commands)
	QueryCommand(commands)
	PingCommand(commands)
