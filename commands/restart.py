from commands.command import Command
from globals import AUTHORIZED_USER
import subprocess
import platform

class RestartCommand(Command):
    COMMAND_NAME = "restart"
    COOLDOWN = 5
    DESCRIPTION = "Restarts the bot. Authorized user only"

    serviceName = "kawaiibotto"
    sudoPassword = "makiisthebestgirl"

    def execute(self, bot, messageData):
        if messageData.user != AUTHORIZED_USER:
            bot.send_message(messageData.channel, f"{messageData.user}, only the authorized user can restart the bot!")
            return
        if platform.system() != "Linux":
            bot.send_message(messageData.channel, f"{messageData.user}, this command is configured to work with Linux only.")
            return
        
        try:
            bot.send_message(messageData.channel, f"{messageData.user}, restarting...")

            subprocess.run(
                ["sudo", "-S", "systemctl", "restart", self.serviceName],
                input=self.sudoPassword + "\n",
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            bot.send_message(messageData.channel, f"{messageData.user}, error when restarting the bot.")

        