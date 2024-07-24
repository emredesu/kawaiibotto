from commands.command import Command, WhisperComand
from globals import AUTHORIZED_USER

class EchoCommand(Command):
    COMMAND_NAME = "echo"
    COOLDOWN = 0
    DESCRIPTION = "Echo the inputted message."

    def execute(self, bot, messageData):
        if messageData.user != AUTHORIZED_USER:
            return

        targetChannel = messageData.channel

        args = messageData.content.split()
        args.pop(0)

        for arg in args:
            if arg.startswith("ch:"):
                targetChannel = arg[3::]
                args.remove(arg)
                break

        bot.send_message(targetChannel, " ".join(args))
    
class EchoWhisperCommand(Command, WhisperComand):
    COMMAND_NAME = ["echo", "echowhisper"]
    COOLDOWN = 0
    DESCRIPTION = "Echo the inputted message through whispers."

    def execute(self, bot, messageData):
        if messageData.whisperUser != AUTHORIZED_USER:
            return
        
        targetChannel = ""

        args = messageData.whisperContent.split()
        args.pop(0)

        for arg in args:
            if arg.startswith("ch:"):
                targetChannel = arg[3::]
                args.remove(arg)
                break

        if targetChannel == "":
            bot.send_whisper(messageData, "You didn't specify a channel!")
        else:
            bot.send_message(targetChannel, " ".join(args))