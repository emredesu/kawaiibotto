from commands.command import Command
import messagetypes
from globals import GOOGLE_GEMINI_APIKEY
import time
from typing import Dict
import google.genai as GenAI
from google.genai import types

class GeminiChatHistory:
    def __init__(self, chatSessionVal, lastActiveTimeVal: float):
        self.chatSession = chatSessionVal # Google made a really cool library that keeps track of the chat history for us, so we just need to keep track of when it was last active. 
        self.lastActiveTime = lastActiveTimeVal

class GeminiCommand(Command):
    COMMAND_NAME = ["gmn", "gemini"]
    COOLDOWN = 5
    DESCRIPTION = "Talk to Google's Gemini! Your messages sent through this command will be kept in the bot's memory for 5 minutes for use in continued \
					conversations with the bot. If you wish to erase the bot's memory of your messages and start fresh, append history:false to your message."

    HISTORY_DURATION = 300
    HISTORY_WIPE_TAG = "history:false"
    HISTORY_EMOJI = "⌛ "

    maxTokens = 2048
    currentModel = "gemini-2.5-flash"
    MAX_RESPONSE_CHARS = 480
    maxRetries = 10

    messageHistory: Dict[str, GeminiChatHistory] = {}

    MASTER_PROMPT = "Keep messages under 250 characters unless the user explicitly asks you for a detailed response. Never respond with more than 500 characters otherwise."

    def __init__(self, commands):
        super().__init__(commands)

        self.geminiClient = GenAI.Client(api_key=GOOGLE_GEMINI_APIKEY)

        # support for google search and remove all safety settings
        groundingTool = types.Tool(google_search=types.GoogleSearch())
        self.config = types.GenerateContentConfig(
                                                max_output_tokens=self.maxTokens,
                                                system_instruction=self.MASTER_PROMPT,
                                                tools=[groundingTool],
                                                safety_settings=[
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                ])
    
    def StartChat(self, username: str):
        self.messageHistory[username] = GeminiChatHistory(self.geminiClient.chats.create(model=self.currentModel, history=[], config=self.config), time.time())

    def execute(self, bot, messageData):
        args = messageData.content.split()
        args.pop(0) # Get rid of the command invocation

        # Check if the history clear tag is inside the tags. If so, clear the user message history.
        if self.HISTORY_WIPE_TAG in args:
            args.pop(args.index(self.HISTORY_WIPE_TAG))
            self.messageHistory.pop(messageData.user)

        userPrompt = " ".join(args)

        hasActiveHistory = False

        success = False

        # Check if the user is inside the messageHistory dict.
        if messageData.user in self.messageHistory:
            # If the user is inside the messageHistory dict, check if it's active (last active time is less than history duration). If so, use this ChatSession object.
            if (time.time() - self.messageHistory[messageData.user].lastActiveTime) < self.HISTORY_DURATION:
                self.messageHistory[messageData.user].lastActiveTime = time.time() # Update last active time.
                hasActiveHistory = True
            # Otherwise, create a new messageHistory object for the user with their prompt.
            else:
                self.StartChat(messageData.user)
        # Create a new messageHistory object for the user with their prompt.
        else:
            self.StartChat(messageData.user)

        for i in range(self.maxRetries):
            try:
                response = self.messageHistory[messageData.user].chatSession.send_message(userPrompt)
                reply_text = response.text if getattr(response, "text", None) else None
                if not reply_text:
                    continue
                else:
                    # Enforce hard character limit to respect MASTER_PROMPT instructions
                    if len(reply_text) > self.MAX_RESPONSE_CHARS:
                        reply_text = reply_text[:self.MAX_RESPONSE_CHARS] + "..."

                    bot.send_message(messageData.channel, f"{messageData.user}, {self.HISTORY_EMOJI if hasActiveHistory else ''} {reply_text}")
                    success = True
                    break
            except Exception as e:
                continue
        
        if not success:
            bot.send_message(messageData.channel, f"{messageData.user}, Currently unable to respond. Please try again later.")

