from commands.command import Command
from globals import OCR_SPACE_APIKEY
import requests

class OCRCommand(Command):
    COMMAND_NAME = "ocr"
    COOLDOWN = 30
    DESCRIPTION = "Use OCR (optical character recognition) to extract the text from an image link. You can specify the language" \
                "using \"lang:(language code here)\". Example usage: _ocr https://i.nuuls.com/leMKr.png lang:jpn"

    def execute(self, bot, user, message, channel):
        target_language = "eng"

        message_args = message.split()
        message_args.pop(0) # Get rid of the first arg that's used to invoke the command.
        for arg in message_args:
            if arg.startswith("lang:"):
                target_language = arg[5:]
                message_args.remove(arg)

        targetRequest = f"https://api.ocr.space/parse/imageurl?apikey={OCR_SPACE_APIKEY}&url={message_args[0]}"
        if target_language != "eng":
            targetRequest += f"&language={target_language}"

        try:
            requestData = requests.get(targetRequest)
            if requestData.status_code != 200:
                bot.send_message(channel, f"{user}, the OCR API returned a {requestData.status_code}.")

            jsonData = requestData.json()
            
            if jsonData["IsErroredOnProcessing"]:
                errorMessage = " / ".join(jsonData["ErrorMessage"])
                bot.send_message(channel, f"{user}, {errorMessage}")
            else:
                parsedText = jsonData["ParsedResults"][0]["ParsedText"]
                if not parsedText:
                    bot.send_message(channel, f"{user}, received empty response from the API, did you give the correct language code with lang:code ?")
                    return
                else:
                    bot.send_message(channel, f"{user}, {parsedText}")
        except:
            bot.send_message(channel, f"{user}, an unknown error has occured.")
        