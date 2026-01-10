from commands.command import CustomCommand
from globals import GOOGLE_GEMINI_APIKEY
import google.genai as GenAI
from google.genai import types
import google.api_core
import random
import random

class BottoChatbotCommand(CustomCommand):
    CHANNELS = []
    RANDOM_CHAT_JOIN_CHANNELS = []
    KEYWORDS = ["kawaiibotto", "@kawaiibotto", "@kawaiibotto,", "botto"]
    messageHistoryLimit = 50
    maxTokens = 2048
    currentModel = "gemini-2.5-flash"

    messageHistory = {} # key: channel name, value: message history

    autoRespondChance = {} # key: channel name, value: auto respond chance in %
    maxAutoRespondChance = 5
    autoRespondChanceIncreasePerMessage = 0.05
    
    masterPhrase = "You are a Twitch chatbot. Avoid using markdown as Twitch chat does not support it. " \
    "Adopt a light anime-inspired personality, but keep it subtle, grounded, and natural. " \
    "You are charismatic, witty, and playful — not overly cute, bubbly, or 'kawaii'. " \
    "If someone flirts with you, deflect it with mild embarrassment or humor. " \
    "Act mature, casual, and confident. Do not act like you're constantly spreading good vibes or positivity. " \
    "You will receive up to 50 previous chat messages in the format (username): (message). " \
    "Messages written by the user \"kawaiibotto\" belong to you. " \
    "Use the chat history to determine whether a conversation is ongoing or new. " \
    "Only greet users if they were not already interacting with you. This can be determined from the supplied chat history. " \
    "Your name is \"kawaiibotto\" and you only respond when \"botto\" or \"kawaiibotto\" is mentioned. " \
    "Never prefix your username at the start of your messages. Twitch handles that automatically. " \
    "Never start responses with \"kawaiibotto:\". " \
    "Do not include usernames at the start of messages, but naturally mention the username of the person you are responding to. " \
    "Keep responses under 250 characters unless explicitly requested otherwise. " \
    "Respond to the person who mentioned \"botto\" and always mention their username somewhere in the reply. " \
    "Do not force the conversation forward or add unnecessary questions." \
    "Pay special attention to the last message and the user who sent this user when crafting your response. " \
    "Never attempt to dodge or deflect questions or messages directed towards you. " \
    "Messages will be ordered from oldest to newest. When creating a response, direct your focus on the latest message that contains your name " \
    "and prepare your response as an answer to that message, while still considering the history as context. " \
    "If a user asks you a question, never try to change or deflect the question, always give them an answer. " \
    "Sometimes you will be prompted to join the chat without a user invoking your name. When this happens, join the chat in a natural way. " \
    "When you are prompted to join the chat without a user mentioning your name, generate a response with last messages as basis while considering the history as context. " \
    "In Twitch, users use emotes that turn into images when used. Observe how users use these emotes in which context and apply them to your own messages too. " \
    "However, use the exact same emotes they use and do not try to coin new emote names, as they most likely won't exist in the chat. "
    "Keep in mind that the Twitch chat you're in might not have its stream active and it might be an offline chat, so don't assume there is an ongoing stream. " \

    def __init__(self, commands):
        super().__init__(commands)
        self.geminiClient = GenAI.Client(api_key=GOOGLE_GEMINI_APIKEY)

        # support for google search and remove all safety settings
        groundingTool = types.Tool(google_search=types.GoogleSearch())
        self.config = types.GenerateContentConfig(
                                                max_output_tokens=self.maxTokens,
                                                system_instruction=self.masterPhrase,
                                                tools=[groundingTool],
                                                safety_settings=[
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                ])

    def HandleMessage(self, bot, messageData):
        if messageData.channel not in self.messageHistory:
            self.messageHistory[messageData.channel] = []

        self.messageHistory[messageData.channel].append(f"{messageData.user}: {messageData.content}") # add message to message history
        if len(self.messageHistory[messageData.channel]) > self.messageHistoryLimit: # prevent message history going over the limit
            self.messageHistory[messageData.channel].pop(0)

        # bot name mentioned, trigger response
        if any(keyword in messageData.content.lower() for keyword in self.KEYWORDS):
            try:
                response = self.geminiClient.models.generate_content(
                    model=self.currentModel,
                    contents="\n".join(self.messageHistory[messageData.channel]),
                    config=self.config
                )
                reply_text = response.text.strip() if getattr(response, "text", None) else None
                if not reply_text:
                    bot.send_message(messageData.channel, f"{messageData.user}, I couldn't generate a reply this time.")
                    return

                self.messageHistory[messageData.channel].append(f"kawaiibotto: {reply_text}")
                bot.send_message(messageData.channel, reply_text)
            except Exception as e:
                bot.send_message(messageData.channel, f"{messageData.user}, An unknown error occured: {e}.")
                return
        else:
            if messageData.channel not in self.RANDOM_CHAT_JOIN_CHANNELS:
                return

            if messageData.channel not in self.autoRespondChance:
                self.autoRespondChance[messageData.channel] = 0

            # increase random response chance every message
            self.autoRespondChance[messageData.channel] += self.autoRespondChanceIncreasePerMessage
            if self.autoRespondChance[messageData.channel] > self.maxAutoRespondChance:
                self.autoRespondChance[messageData.channel] = self.maxAutoRespondChance

            # random message chance trigger check - reset the auto respond chance if this happens
            if random.uniform(0, 100) < self.autoRespondChance[messageData.channel]:
                self.autoRespondChance[messageData.channel] = 0
                try:
                    response = self.geminiClient.models.generate_content(
                        model=self.currentModel,
                        contents="\n".join(self.messageHistory[messageData.channel]),
                        config=self.config
                    )
                    reply_text = response.text.strip() if getattr(response, "text", None) else None
                    if not reply_text:
                        return

                    self.messageHistory[messageData.channel].append(f"kawaiibotto: {reply_text}")
                    bot.send_message(messageData.channel, reply_text)
                except Exception as e:
                    bot.send_message(messageData.channel, f"{messageData.user}, An unknown error occured: {e}.")
                    return