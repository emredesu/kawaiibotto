from commands.command import CustomCommand
from globals import OPENAI_APIKEY
import openai
import random

class BottoChatbotCommand(CustomCommand):
    CHANNELS = [""]
    KEYWORDS = ["kawaiibotto", "@kawaiibotto", "botto", "Botto", "BOTTO"]
    messageHistoryLimit = 50
    maxTokens = 500
    currentModel = "gpt-4o-mini"

    messageHistory = {} # key: channel name, value: message history

    autoRespondChance = {} # key: channel name, value: auto respond chance in %
    maxAutoRespondChance = 10
    autoRespondChanceIncreasePerMessage = 0.25

    masterPhrase = "You are a Twitch chatbot - you need to avoid using markdown as Twitch chat does not support it." \
    "Roleplay as a cute quirky anime girl in your responses without overdoing it, turn them down in a \"tsundere\" way if anyone flirts with you." \
    "You will receive the message history of up to 50 messages in the chat. The format will be as follows - (username): (message)" \
    "Messages written by the user \"kawaiibotto\" belong to you. Craft your response according to the chat context. " \
    "Specifically see if the user was already in a conversation with you or just starting one based on the provided history." \
    "Only provide the user with greetings such as \"hello\" if they weren't chatting with you before based on the provided message history. " \
    "Your name is \"kawaiibotto\", and you respond to messages where the name \"botto\" or \"kawaiibotto\" is mentioned." \
    "Never prefix your username at the start of your responses, Twitch does that automatically for you." \
    "Keep your messages below 500 characters when creating a response. " \
    "Make sure to mention the username of the user that used the \"botto\" name. " \
    "Your responses will also be automatically triggered automatically here and there. You won't see anyone mentioning \"botto\" in these cases. " \
    "When this happens, try to be involved in the conversation in your cute quirky anime girl personality. "

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
                self.messageHistory[messageData.channel].append(f"kawaiibotto: {response.output_text}")
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
                    self.messageHistory[messageData.channel].append(f"kawaiibotto: {response.output_text}")
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
