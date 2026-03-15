from commands.command import Command
from globals import AUTHORIZED_USER, SUDO_PASSWORD
import subprocess
import platform


def restart_bot_service(service_name):
    subprocess.run(
        ["sudo", "-S", "systemctl", "restart", service_name],
        input=SUDO_PASSWORD + "\n",
        text=True,
        check=True
    )

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
            restart_bot_service(self.serviceName)
        except subprocess.CalledProcessError:
            bot.send_reply_message(messageData, f"Error when restarting the bot.")

        