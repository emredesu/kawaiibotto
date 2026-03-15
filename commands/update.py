from commands.command import Command
from commands.restart import RestartCommand, restart_bot_service
from globals import AUTHORIZED_USER
from pathlib import Path
import platform
import subprocess


class UpdateCommand(Command):
    COMMAND_NAME = "update"
    COOLDOWN = 5
    DESCRIPTION = "Pulls latest changes from GitHub and restarts the bot. Authorized user only"

    REPOSITORY_URL = "https://github.com/emredesu/kawaiibotto"

    def _run_git_command(self, repo_path, args):
        return subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=True,
            capture_output=True,
            text=True
        )

    def _has_local_changes(self, repo_path):
        status_output = self._run_git_command(repo_path, ["status", "--porcelain"]).stdout.strip()
        return status_output != ""

    def execute(self, bot, messageData):
        if messageData.user != AUTHORIZED_USER:
            bot.send_reply_message(messageData, f"Only the authorized user can update the bot!")
            return

        if platform.system() != "Linux":
            bot.send_reply_message(messageData, f"This command is configured to work with Linux only.")
            return

        repo_path = Path(__file__).resolve().parent.parent
        bot.send_reply_message(messageData, "Checking repository for updates...")

        stashed_local_changes = False

        try:
            self._run_git_command(repo_path, ["rev-parse", "--is-inside-work-tree"])
            current_branch = self._run_git_command(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

            if self._has_local_changes(repo_path):
                bot.send_reply_message(messageData, "Local changes detected. Stashing them before update...")
                self._run_git_command(repo_path, ["stash", "push", "--include-untracked", "-m", "kawaiibotto auto update stash"])
                stashed_local_changes = True

            pull_result = self._run_git_command(repo_path, ["pull", "--ff-only", self.REPOSITORY_URL, current_branch])
        except FileNotFoundError:
            bot.send_reply_message(messageData, "Update failed: git is not installed on this system.")
            return
        except subprocess.CalledProcessError as error:
            if stashed_local_changes:
                try:
                    self._run_git_command(repo_path, ["stash", "pop"])
                except subprocess.CalledProcessError:
                    bot.send_reply_message(messageData, "Update failed, and local changes are still in stash. Restore them manually with git stash pop.")
                    return

            git_error_output = (error.stderr or error.stdout or "unknown git error").strip()
            bot.send_reply_message(messageData, f"Update failed: {git_error_output[:300]}")
            return

        if stashed_local_changes:
            try:
                self._run_git_command(repo_path, ["stash", "pop"])
            except subprocess.CalledProcessError as error:
                git_error_output = (error.stderr or error.stdout or "unknown git error").strip()
                bot.send_reply_message(messageData, f"Update pulled, but local changes could not be reapplied cleanly: {git_error_output[:220]}")
                return

        pull_output = (pull_result.stdout + pull_result.stderr).strip().lower()
        if "already up to date" in pull_output or "already up-to-date" in pull_output:
            bot.send_reply_message(messageData, "No updates found. Bot will continue running without restart.")
            return

        try:
            bot.send_reply_message(messageData, "Update pulled successfully. Restarting bot service...")
            restart_bot_service(RestartCommand.serviceName)
        except subprocess.CalledProcessError:
            bot.send_reply_message(messageData, "Update was pulled, but restarting the bot failed.")
