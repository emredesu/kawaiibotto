from commands.command import CustomCommand

class QuoteRespondsCommand(CustomCommand):
    colonThreeChannel = ""

    CHANNELS = [colonThreeChannel]

    def HandleMessage(self, bot, messageData):
        if messageData.channel.lower() == self.colonThreeChannel and messageData.content == ":3":
            bot.send_message(messageData.channel, ":3")