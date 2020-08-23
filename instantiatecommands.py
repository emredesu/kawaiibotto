from commands.helloworld import HelloWorldCommand
from commands.pyramid import PyramidCommand
from commands.ivrfi_api_commands import RandomQuoteCommand, EmoteInfoCommand
from commands.opgg import OpggCommand
from commands.twitch_api_commands import UserIDCommand, ProfilePictureCommand, EmotesCommand
from commands.query import QueryCommand
from commands.ping import PingCommand
from commands.sourcecode import SourceCodeCommand
from commands.commands import CommandsCommand
from commands.help import HelpCommand
from commands.code import CodeCommand
from commands.math import MathCommand


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
	SourceCodeCommand(commands)
	CommandsCommand(commands)
	HelpCommand(commands)
	CodeCommand(commands)
	ProfilePictureCommand(commands)
	MathCommand(commands)
