from commands.command import Command


class EchoCommand(Command):
    COMMAND_NAME = "echo"
    COOLDOWN = 0
    DESCRIPTION = "Echo the inputted message."

    def execute(self, bot, user, message, channel):
        if user != "emredesu":
            return

        targetChannel = channel

        args = message.split()
        args.pop(0)

        for arg in args:
            if arg.startswith("ch:"):
                targetChannel = arg[3::]
                args.remove(arg)
                break

        bot.send_message(targetChannel, " ".join(args))