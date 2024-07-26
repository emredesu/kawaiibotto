from commands.helloworld import HelloWorldCommand
from commands.ivrfi_api_commands import RandomQuoteCommand, EmoteInfoCommand
from commands.opgg import OpggCommand
from commands.twitch_api_commands import UserIDCommand, ProfilePictureCommand, EmotesCommand
from commands.query import QueryCommand
from commands.ping import PingCommand
from commands.sourcecode import SourceCodeCommand
from commands.commands import CommandsCommand
from commands.help import HelpCommand
from commands.code import CodeCommand
from commands.translate import TranslateCommand
from commands.urban import UrbanCommand
from commands.define import DefineCommand
from commands.ocr import OCRCommand
from commands.genshin import GenshinCommand
from commands.echo import EchoCommand, EchoWhisperCommand
from commands.maths import MathsCommand
from commands.gpt import ChatBotCommand
from commands.hoyoGameData import GenshinResinCheckCommand, HonkaiStarRailStaminaCheckCommand, ZenlessZoneZeroEnergyCheckCommand, HoyolabRegistrationCommand, HoyolabRegistrationWhisperCommand, HoyoGameDailyRewardClaimCommand
from commands.gemini import GeminiCommand

def instantiate_commands(commands):
	# PRIVMSG commands
	HelloWorldCommand(commands)
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
	TranslateCommand(commands)
	UrbanCommand(commands)
	DefineCommand(commands)
	OCRCommand(commands)
	GenshinCommand(commands)
	EchoCommand(commands)
	MathsCommand(commands)
	ChatBotCommand(commands)
	GenshinResinCheckCommand(commands)
	HonkaiStarRailStaminaCheckCommand(commands)
	ZenlessZoneZeroEnergyCheckCommand(commands)
	GeminiCommand(commands)
	HoyolabRegistrationCommand(commands)
	HoyoGameDailyRewardClaimCommand(commands)

def instantiate_whisper_commands(commands):
	EchoWhisperCommand(commands)
	HoyolabRegistrationWhisperCommand(commands)
