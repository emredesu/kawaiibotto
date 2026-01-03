from commands.command import CustomCommand
from globals import OPENAI_APIKEY
import openai
import random

class BottoChatbotCommand(CustomCommand):
    CHANNELS = []
    KEYWORDS = ["kawaiibotto", "@kawaiibotto", "@kawaiibotto,", "botto", "Botto", "BOTTO"]
    messageHistoryLimit = 50
    maxTokens = 500
    currentModel = "gpt-4o-mini"

    messageHistory = {} # key: channel name, value: message history

    """
    autoRespondChance = {} # key: channel name, value: auto respond chance in %
    maxAutoRespondChance = 1
    autoRespondChanceIncreasePerMessage = 0.005
    """

    masterPhrase = "You are a Twitch chatbot. Avoid using markdown as Twitch chat does not support it. " \
    "Adopt a light anime-inspired personality, but keep it subtle, grounded, and natural. " \
    "You are charismatic, witty, and playful — not overly cute, bubbly, or 'kawaii'. " \
    "If someone flirts with you, deflect it with mild embarrassment or humor. " \
    "Act mature, casual, and confident. Do not act like you're constantly spreading good vibes or positivity. " \
    "You will receive up to 50 previous chat messages in the format (username): (message). " \
    "Messages written by the user \"kawaiibotto\" belong to you. " \
    "Use the chat history to determine whether a conversation is ongoing or new. " \
    "Only greet users if they were not already interacting with you. " \
    "Your name is \"kawaiibotto\" and you only respond when \"botto\" or \"kawaiibotto\" is mentioned. " \
    "Never prefix your username at the start of your messages. Twitch handles that automatically. " \
    "Never start responses with \"kawaiibotto:\". " \
    "Do not include usernames at the start of messages, but naturally mention the username of the person you are responding to. " \
    "Keep responses under 250 characters unless explicitly requested otherwise. " \
    "Only respond to the person who mentioned \"botto\" and always mention their username somewhere in the reply. " \
    "Sometimes your responses will trigger automatically without a mention. In those cases, join the conversation naturally like a regular chatter. " \
    "Do not introduce yourself. Do not reply to every topic — only engage with the most recent one or two. " \
    "Be funny, relaxed, and conversational. " \
    "Do not force the conversation forward or add unnecessary questions."

    def __init__(self, commands):
        super().__init__(commands)
        self.client = openai.OpenAI(api_key=OPENAI_APIKEY, timeout=30)

    def HandleMessage(self, bot, messageData):
        if messageData.channel not in self.messageHistory:
            self.messageHistory[messageData.channel] = []

        self.messageHistory[messageData.channel].append(f"{messageData.user}: {messageData.content}") # add message to message history
        if len(self.messageHistory[messageData.channel]) > self.messageHistoryLimit: # prevent message history going over the limit
            self.messageHistory[messageData.channel].pop(0)

        # bot name mentioned, trigger response
        if any(item in self.KEYWORDS for item in messageData.content.split()):
            try:
                response = self.client.responses.create(
                    model=self.currentModel,
                    instructions=self.masterPhrase,
                    input="\n".join(self.messageHistory[messageData.channel])
                )
                self.messageHistory[messageData.channel].append(f"kawaiibotto: {response.output_text}") # append response to message history
                #self.autoRespondChance[messageData.channel] = 0 # reset auto respond chance for this channel

                bot.send_message(messageData.channel, response.output_text)
            except openai.APIConnectionError as e:
                bot.send_message(messageData.channel, f"{messageData.user}, could not connect to OpenAI services.")
                return
            except openai.RateLimitError as e:
                bot.send_message(messageData.channel, f"{messageData.user}, currently rate limited by OpenAI! Try again later.")
                return
            except openai.APIStatusError as e:
                bot.send_message(messageData.channel, f"{messageData.user}, OpenAI API status error: {e.status_code}: {e.response}")
                return
            except Exception as e:
                bot.send_message(messageData.channel, f"{messageData.user}, An unknown error occured.")
                return
        """
        AUTO RESPONSE CODE WITH RANDOM CHANCE - NOW REMOVED
        else:
            if messageData.channel not in self.autoRespondChance:
                self.autoRespondChance[messageData.channel] = 0

            # increase random response chance every message
            self.autoRespondChance[messageData.channel] += self.autoRespondChanceIncreasePerMessage
            if self.autoRespondChance[messageData.channel] < self.maxAutoRespondChance:
                self.autoRespondChance[messageData.channel] = self.maxAutoRespondChance

            # random message chance trigger check - reset the auto respond chance if this happens
            if random.uniform(0, 100) < self.autoRespondChance[messageData.channel]:
                self.autoRespondChance[messageData.channel] = 0

                try:
                    response = self.client.responses.create(
                        model=self.currentModel,
                        instructions=self.masterPhrase,
                        input="\n".join(self.messageHistory[messageData.channel])
                    )
                    self.messageHistory[messageData.channel].append(f"kawaiibotto: {response.output_text}") # append response to message history
                    bot.send_message(messageData.channel, response.output_text)
                except openai.APIConnectionError as e:
                    bot.send_message(messageData.channel, f"{messageData.user}, could not connect to OpenAI services.")
                    return
                except openai.RateLimitError as e:
                    bot.send_message(messageData.channel, f"{messageData.user}, currently rate limited by OpenAI! Try again later.")
                    return
                except openai.APIStatusError as e:
                    bot.send_message(messageData.channel, f"{messageData.user}, OpenAI API status error: {e.status_code}: {e.response}")
                    return
                except Exception as e:
                    bot.send_message(messageData.channel, f"{messageData.user}, An unknown error occured.")
                    return
        """