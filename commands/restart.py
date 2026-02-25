from commands.command import Command
from globals import AUTHORIZED_USER, SUDO_PASSWORD
import subprocess
import platform

class RestartCommand(Command):
    COMMAND_NAME = "restart"
    COOLDOWN = 5
    DESCRIPTION = "Restarts the bot. Authorized user only"

    serviceName = "kawaiibotto"

    def execute(self, bot, messageData):
        if messageData.user != AUTHORIZED_USER:
            bot.send_reply_message(messageData, f"Only the authorized user can restart the bot!")
            return
        if platform.system() != "Linux":
            bot.send_reply_message(messageData, f"This command is configured to work with Linux only.")
            return
        
        try:
            bot.send_reply_message(messageData, f"Restarting...")

            subprocess.run(
                ["sudo", "-S", "systemctl", "restart", self.serviceName],
                input=SUDO_PASSWORD + "\n",
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            bot.send_reply_message(messageData, f"Error when restarting the bot.")

        