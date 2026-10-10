from commands.command import CustomCommand
import time

class QuoteRespondsCommand(CustomCommand):
    baseChannel = "emredesu"
    
    colonThreeChannel = "kimimayushi"
    colonThreeCooldown = 10
    colonThreeLastTriggerTime = 0

    CHANNELS = [baseChannel, colonThreeChannel]

    def HandleMessage(self, bot, messageData):
        if (messageData.channel.lower() == self.colonThreeChannel and messageData.content == ":3") and self.colonThreeLastTriggerTime + self.colonThreeCooldown < time.time():
            bot.send_message(messageData.channel, ":3")
            self.colonThreeLastTriggerTime = time.time()

        if (messageData.channel.lower() == "emredesu" and "emgay" in messageData.content):
            bot.send_message(messageData.channel, "emstraight")
