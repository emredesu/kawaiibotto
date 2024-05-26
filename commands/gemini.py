from commands.command import Command
import messagetypes
from globals import GOOGLE_GEMINI_APIKEY
import time
from typing import Dict
import google.generativeai as GenAI

class GeminiChatHistory:
    def __init__(self, chatSessionVal: GenAI.ChatSession, lastActiveTimeVal: float):
        self.chatSession = chatSessionVal # Google made a really cool library that keeps track of the chat history for us, so we just need to keep track of when it was last active. 
        self.lastActiveTime = lastActiveTimeVal

class GeminiCommand(Command):
    COMMAND_NAME = ["gmn", "gemini"]
    COOLDOWN = 5
    DESCRIPTION = "Talk to Google's Gemini! Your messages sent through this command will be kept in the bot's memory for 5 minutes for use in continued \
					conversations with the bot. If you wish to erase the bot's memory of your messages and start fresh, append history:false to your message."
    
    USED_MODEL = "gemini-1.5-flash-latest"

    HISTORY_DURATION = 300
    HISTORY_WIPE_TAG = "history:false"
    HISTORY_EMOJI = "⌛ "

    messageHistory: Dict[str, GeminiChatHistory] = {}

    MASTER_PROMPT = "Keep messages under 500 characters unless the user specifically asks for a more detailed response."
    
    def __init__(self, commands):
        super().__init__(commands)

        GenAI.configure(api_key=GOOGLE_GEMINI_APIKEY)
        self.model = GenAI.GenerativeModel(model_name=self.USED_MODEL, system_instruction=self.MASTER_PROMPT)

    def execute(self, bot, messageData):
        args = messageData.content.split()
        args.pop(0) # Get rid of the command invocation

        # Check if the history clear tag is inside the tags. If so, clear the user message history.
        if self.HISTORY_WIPE_TAG in args:
            args.pop(args.index(self.HISTORY_WIPE_TAG))
            self.messageHistory.pop(messageData.user)

        userPrompt = " ".join(args)

        hasActiveHistory = False 

        try:
            # Check if the user is inside the messageHistory dict.
            if messageData.user in self.messageHistory:
                # If the user is inside the messageHistory dict, check if it's active (last active time is less than history duration). If so, use this ChatSession object.
                if (time.time() - self.messageHistory[messageData.user].lastActiveTime) < self.HISTORY_DURATION:
                    self.messageHistory[messageData.user].lastActiveTime = time.time() # Update last active time.
                    hasActiveHistory = True
                    pass
                # Otherwise, create a new messageHistory object for the user with their prompt.
                else:
                    self.messageHistory[messageData.user] = GeminiChatHistory(self.model.start_chat(history=[]), time.time())
            # Create a new messageHistory object for the user with their prompt.
            else:
                self.messageHistory[messageData.user] = GeminiChatHistory(self.model.start_chat(history=[]), time.time())

            response = self.messageHistory[messageData.user].chatSession.send_message(userPrompt)
            bot.send_message(messageData.channel, f"{messageData.user}, {self.HISTORY_EMOJI if hasActiveHistory else ''} {response.text}")
        except GenAI.types.StopCandidateException:
            bot.send_message(messageData.channel, f"{messageData.user}, Execution stopped due to safety reasons. Your message history was cleaned.")
            self.messageHistory.pop(messageData.user)
        except GenAI.types.BlockedPromptException:
            bot.send_message(messageData.channel, f"{messageData.user}, Execution stopped due to your prompt being blocked. Your message history was cleaned.")
            self.messageHistory.pop(messageData.user)
        except Exception as exception:
            bot.send_message(messageData.channel, f"{messageData.user}, Failed to get a response due to: {type(exception).__name__}. Your message history was cleaned.")
            self.messageHistory.pop(messageData.user)

