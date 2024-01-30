from commands.command import Command
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