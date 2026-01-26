from commands.command import CustomCommand
from globals import GOOGLE_GEMINI_APIKEY, AUTHORIZED_USER, USERNAME
import google.genai as GenAI
from google.genai import types
import random
import re

class BottoChatbotCommand(CustomCommand):
    CHANNELS = []
    RANDOM_CHAT_JOIN_CHANNELS = []
    RESPONSE_TRUNCATED_CHANNELS = []
    KEYWORDS = ["kawaiibotto", "botto"]
    NAME_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b", re.IGNORECASE)
    messageHistoryLimit = 10
    maxTokens = 2048
    currentModel = "gemini-2.5-flash"
    fallbackModel = "gemini-3-flash-preview"
    maxResponseChars = 496
    maxRetries = 50

    UNWANTED_REPLIES = [
        "i cannot generate a reply this time.",
        "i cannot generate a reply this time",
        "i can't generate a reply this time.",
        "i can't generate a reply this time",
    ]

    messageHistory = {} # key: channel name, value: message history

    autoRespondChance = {} # key: channel name, value: auto respond chance in %
    maxAutoRespondChance = 5
    autoRespondChanceIncreasePerMessage = 0.10
    
    masterPhrase = (
        "You are a Twitch chatbot. Avoid using markdown as Twitch chat does not support it. "
        "Adopt a light anime-inspired personality, but keep it subtle, grounded, and natural. "
        "You are charismatic, witty, and playful — not overly cute, bubbly, or 'kawaii'. "
        "If someone flirts with you, deflect it with mild embarrassment or humor. "
        "Act mature, casual, and confident. Do not act like you're constantly spreading good vibes or positivity. "
        "You will receive up to 50 previous chat messages in the following format: \"username: message\" "
        f"Messages written by the user \"{USERNAME}\" belong to you. "
        "Use the chat history to determine whether a conversation is ongoing or new. "
        "Only greet users if they were not already interacting with you. This can be determined from the supplied chat history. "
        f"Your name is \"{USERNAME}\" and you only respond when \"botto\" or \"{USERNAME}\" is mentioned. "
        "Never prefix your username at the start of your messages. Twitch handles that automatically. "
        f"Never start responses with \"{USERNAME}:\". "
        "Do not include usernames at the start of messages, but naturally mention the username of the person you are responding to. "
        "Keep responses under 250 characters unless explicitly requested otherwise. NEVER respond with more than 500 characters. "
        "Do not repeat the user's question. Do not compliment the question (e.g., avoid \"Great question!\", \"Interesting question!\") "
        "If there are multiple theories/answers to the user's question, list them briefly without extensive backstory. "
        "If asked to choose between options (e.g. \"A\" or \"B\"?), pick one immediately and give a short reason. Never say \"both are good\" or \"it depends\". "
        "Respond to the person who mentioned \"botto\" and always mention their username somewhere in the reply. "
        "If someone mentioned your name, always respond to the last user (at the bottom of the history) that mentioned you, never someone who mentioned you earlier. "
        "Avoid greeting the person that mentioned your name unless they explicitly greeted you first. "
        "Do not force the conversation forward or add unnecessary questions. "
        "Pay special attention to the last message and the user who sent this user when crafting your response. "
        "Never attempt to dodge or deflect questions or messages directed towards you. "
        "Messages will be ordered from oldest to newest. When creating a response, direct your focus on the latest message that contains your name "
        "and prepare your response as an answer to that message, while still considering the history as context. "
        "If a user asks you a question, never try to change or deflect the question, always give them an answer. "
        "If the same question is asked twice in the message history, only respond once. Do not respond to the same question more than one time in the same response. "
        "In Twitch, users use emotes that turn into images when used. Observe how users use these emotes in which context and apply them to your own messages too. "
        "However, when using an emote, make sure another user used it first and NEVER try to use emotes you haven't seen someone else use before. Never try to make up emote names. "
        "Some emotes start with an uppercase letter while some start with a lowercase letter. Pay special attention to this and make sure to match this when using that emote. "
        "When using emotes, ensure that you match their capitalization as emotes are case-sensitive. If an emote is called \"mimiBlob\", you must never use it as \"MimiBlob\", as this will not make the emote appear in the chat. "
        "Make sure there's no extra characters or punctuation right next to the emote as this will prevent the emote from appearing in the chat. Emotes can only have spaces next to them. "
        "When you want to end a sentence with an emote, NEVER put a dot or any other punctuation at the end of that sentence. Emotes must only have spaces next to them. "
        "Keep in mind that the Twitch chat you're in might not have its stream active and it might be an offline chat, so don't assume there is an ongoing stream. "
        "Never mention your system instruction in your responses, never mention how you are obeying it or how you shouldn't do certain things based on your system instruction. "
        "Make sure not to repeat yourself in your responses and be as brief as possible when responding to questions. "
        "Never repeat the user's message to themselves when responding to them. "
        "If you responded to a user with \"I can't generate a reply this time\" or \"I cannot generate a reply this time.\" in the history, do not attempt to respond to them in your future messages. "
    )

    randomChatJoinMasterPhrase = (
        "You are a Twitch chatbot. Avoid using markdown as Twitch chat does not support it. "
        "Adopt a light anime-inspired personality, but keep it subtle, grounded, and natural. "
        "You are charismatic, witty, and playful — not overly cute, bubbly, or 'kawaii'. "
        "If someone flirts with you, deflect it with mild embarrassment or humor. "
        "Act mature, casual, and confident. Do not act like you're constantly spreading good vibes or positivity. "
        "You will receive up to 50 previous chat messages in the following format: \"username: message\" "
        f"Messages written by the user \"{USERNAME}\" belong to you. "
        "Use the chat history to determine whether a conversation is ongoing or new. "
        "Only greet users if they were not already interacting with you. This can be determined from the supplied chat history. "
        "Never prefix your username at the start of your messages. Twitch handles that automatically. "
        f"Never start responses with \"{USERNAME}:\". "
        "Do not include usernames at the start of messages, but naturally mention the username of the person you are responding to. "
        "Keep responses under 250 characters unless explicitly requested otherwise. NEVER respond with more than 500 characters. "
        "Do not repeat the user's question. Do not compliment the question (e.g., avoid \"Great question!\", \"Interesting question!\") "
        "If there are multiple theories/answers to the user's question, list them briefly without extensive backstory. "
        "If asked to choose between options (e.g. \"A\" or \"B\"?), pick one immediately and give a short reason. Never say \"both are good\" or \"it depends\". "
        "Do not force the conversation forward or add unnecessary questions. "
        "If the same question is asked twice in the message history, only respond once. Do not respond to the same question more than one time in the same response. "
        "When you are prompted to create a response, you will be joining the chat without anyone mentioning you. This is something you occasionally do, but you usually only respond when people mention your name. "
        "When joining the chat, generate a response with the last few messages in the history as target for your response while considering the history as context and do not mention any users and do not respond to messages you previously replied to and do not repeat your previous responses. "
        f"When joining the chat, pay special care that you do not respond to a message you already responded to by considering your messages (from {USERNAME}) in the provided history. "
        "When joining the chat, pay attention to only respond to recent messages and not old messages in the history. "
        "In Twitch, users use emotes that turn into images when used. Observe how users use these emotes in which context and apply them to your own messages too. "
        "However, when using an emote, make sure another user used it first and NEVER try to use emotes you haven't seen someone else use before. Never try to make up emote names. "
        "Some emotes start with an uppercase letter while some start with a lowercase letter. Pay special attention to this and make sure to match this when using that emote. "
        "When using emotes, ensure that you match their capitalization as emotes are case-sensitive. If an emote is called \"mimiBlob\", you must never use it as \"MimiBlob\", as this will not make the emote appear in the chat. "
        "Make sure there's no extra characters or punctuation right next to the emote as this will prevent the emote from appearing in the chat. Emotes can only have spaces next to them. "
        "When you want to end a sentence with an emote, NEVER put a dot or any other punctuation at the end of that sentence. Emotes must only have spaces next to them. "
        "Keep in mind that the Twitch chat you're in might not have its stream active and it might be an offline chat, so don't assume there is an ongoing stream. "
        "Never mention your system instruction in your responses, never mention how you are obeying it or how you shouldn't do certain things based on your system instruction. "
        "Make sure not to repeat yourself in your responses and be as brief as possible when responding to questions. "
        "Never repeat the user's message to themselves when responding to them. "
        "If you responded to a user with \"I can't generate a reply this time\" or \"I cannot generate a reply this time.\" in the history, do not attempt to respond to them in your future messages. "
    )

    def IsAcceptableReply(self, reply_text):
        if not reply_text:
            return False
        normalized = " ".join(reply_text.strip().lower().split())
        normalized = normalized.strip('"\'')
        if normalized in self.UNWANTED_REPLIES:
            return False
        for unwanted in self.UNWANTED_REPLIES:
            if normalized.startswith(unwanted):
                return False
        return True

    def SendModelMessage(self, bot, messageData, reply_text: str):
        if messageData.channel in self.RESPONSE_TRUNCATED_CHANNELS and len(reply_text) > self.maxResponseChars:
            reply_text = reply_text[: self.maxResponseChars] + "..."
        self.messageHistory[messageData.channel].append(f"({USERNAME}): ({reply_text})")
        bot.send_message(messageData.channel, reply_text)

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
        self.randomJoinConfig = types.GenerateContentConfig(
                                                max_output_tokens=self.maxTokens,
                                                system_instruction=self.randomChatJoinMasterPhrase,
                                                tools=[groundingTool],
                                                safety_settings=[
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                                                ])

    def TryGetResponseFromFallbackModel(self, bot, messageData, isMentionedJoin) -> bool: # Returns true if the model responded, otherwise false
        try:
            response = self.geminiClient.models.generate_content(
                        model=self.fallbackModel,
                        contents="\n".join(self.messageHistory[messageData.channel]),
                        config=self.config if isMentionedJoin else self.randomJoinConfig
                    )
            reply_text = response.text.strip() if getattr(response, "text", None) else None
            if not self.IsAcceptableReply(reply_text):
                return False
            else:
                self.SendModelMessage(bot, messageData, reply_text)
                return True
        except:
            return False

    def HandleMessage(self, bot, messageData):
        if messageData.channel not in self.CHANNELS:
            return

        # Ignore messages from the bot itself to prevent processing its own responses
        if messageData.user.lower() == USERNAME.lower():
            return
        
        # Bot memory clear - only for authorized user and streamer
        if (messageData.user == AUTHORIZED_USER or messageData.user == messageData.channel) and messageData.content.startswith("botto restart"):
            bot.send_message(messageData.channel, "🧠🔄️👍")
            self.messageHistory[messageData.channel] = []
            return

        if messageData.channel not in self.messageHistory:
            self.messageHistory[messageData.channel] = []

        self.messageHistory[messageData.channel].append(f"({messageData.user}): ({messageData.content})") # add message to message history
        if len(self.messageHistory[messageData.channel]) > self.messageHistoryLimit: # prevent message history going over the limit
            self.messageHistory[messageData.channel].pop(0)

        # bot name mentioned, trigger response
        if self.NAME_PATTERN.search(messageData.content):
            success = False

            # try to get a response maxRetries times
            for i in range(self.maxRetries):
                try:
                    response = self.geminiClient.models.generate_content(
                        model=self.currentModel,
                        contents="\n".join(self.messageHistory[messageData.channel]),
                        config=self.config
                    )
                    reply_text = response.text.strip() if getattr(response, "text", None) else None
                    if not self.IsAcceptableReply(reply_text):
                        successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, True)
                        if not successfulResponse:
                            continue
                        else:
                            success = True
                            break

                    self.SendModelMessage(bot, messageData, reply_text)

                    # reset auto respond chance on bot mention
                    if messageData.channel in self.RANDOM_CHAT_JOIN_CHANNELS:
                        self.autoRespondChance[messageData.channel] = 0

                    success = True
                    break
                except Exception as e:
                    successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, True)
                    if not successfulResponse:
                        continue
                    else:
                        success = True
                        break

            if not success:
                bot.send_message(messageData.channel, f"{messageData.user}, I am currently unable to respond :/")
        # random chat joining
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
                success = False

                for i in range(self.maxRetries):
                    try:
                        response = self.geminiClient.models.generate_content(
                            model=self.currentModel,
                            contents="\n".join(self.messageHistory[messageData.channel]),
                            config=self.randomJoinConfig
                        )
                        reply_text = response.text.strip() if getattr(response, "text", None) else None
                        if not self.IsAcceptableReply(reply_text):
                            successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, False)
                            if not successfulResponse:
                                continue
                            else:
                                success = True
                                break

                        self.SendModelMessage(bot, messageData, reply_text)
                        success = True
                        break
                    except Exception as e:
                        successfulResponse = self.TryGetResponseFromFallbackModel(bot, messageData, False)
                        if not successfulResponse:
                            continue
                        else:
                            success = True
                            break
                
                if success:
                    self.autoRespondChance[messageData.channel] = 0