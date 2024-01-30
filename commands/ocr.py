from commands.command import Command
from globals import OCR_SPACE_APIKEY
import requests

class OCRCommand(Command):
    COMMAND_NAME = "ocr"
    COOLDOWN = 10
    DESCRIPTION = "Use OCR (optical character recognition) to extract the text from an image link. You can specify the language" \
                "using \"lang:(language code here)\". Example usage: _ocr https://i.nuuls.com/leMKr.png lang:jpn"

    def execute(self, bot, messageData):
        target_language = "eng"

        message_args = messageData.content.split()
        message_args.pop(0) # Get rid of the first arg that's used to invoke the command.
        for arg in message_args:
            if arg.startswith("lang:"):
                target_language = arg[5:]
                message_args.remove(arg)

        validLanguageCodes = ["ara", "bul", "chs", "cht", "hrv", "cze", "dan", "dut", "eng", "fin", "fre", "ger", "gre", "hun", "kor", "ita", "jpn", "pol", "por", "rus", "slv", "spa", "swe", "tur"]

        # A dictionary that converts full language names and two letter codes into three letter codes.
        matchedLanguageCodes = {
            "arabic": "ara",
            "ar": "ara",
            "bulgarian": "bul",
            "bg": "bul",
            "chinese": "chs",
            "ch": "chs",
            "chinesetraditional": "cht",
            "crotian": "hrv",
            "hr": "hrv",
            "czech": "cze",
            "cz": "cze",
            "danish": "dan",
            "da": "dan",
            "dutch": "dut",
            "nl": "dut",
            "english": "eng",
            "en": "eng",
            "finnish": "fin",
            "fi": "fin",
            "german": "ger",
            "de": "ger",
            "hungarian": "hun",
            "hu": "hun",
            "korean": "kor",
            "ko": "kor",
            "italian": "ita",
            "it": "ita",
            "japanese": "jpn",
            "ja": "jpn",
            "polish": "pol",
            "pl": "pol",
            "portuguese": "por",
            "pt": "por",
            "russian": "rus",
            "ru": "rus",
            "slovenian": "slv",
            "sl": "slv",
            "spanish": "spa",
            "es": "spa",
            "swedish": "swe",
            "sv": "swe",
            "turkish": "tur",
            "tr": "tur"
        }

        # Check if the user has inputted a valid language code. If not, try to match it with a commonly used language code. 
        if target_language not in validLanguageCodes:
            try:
                target_language = matchedLanguageCodes[target_language]
            except KeyError:
                bot.send_message(messageData.channel, f"{messageData.user}, the language code you inputted is invalid. Valid codes can be found at: https://ocr.space/OCRAPI#:~:text=faster%20upload%20speeds.-,language,-%5BOptional%5D%0AArabic")
                return

        targetRequest = f"https://api.ocr.space/parse/imageurl?apikey={OCR_SPACE_APIKEY}&url={message_args[0]}"
        if target_language != "eng":
            targetRequest += f"&language={target_language}"

        try:
            requestData = requests.get(targetRequest)
            if requestData.status_code != 200:
                bot.send_message(messageData.channel, f"{messageData.user}, the OCR API returned a {requestData.status_code}.")

            jsonData = requestData.json()
            
            if jsonData["IsErroredOnProcessing"]:
                errorMessage = " / ".join(jsonData["ErrorMessage"])
                bot.send_message(messageData.channel, f"{messageData.user}, {errorMessage}")
            else:
                parsedText = jsonData["ParsedResults"][0]["ParsedText"]
                if not parsedText:
                    bot.send_message(messageData.channel, f"{messageData.user}, received empty response from the API, did you give the correct language code with lang:code ?")
                    return
                else:
                    bot.send_message(messageData.channel, f"{messageData.user}, {parsedText}")
        except:
            bot.send_message(messageData.channel, f"{messageData.user}, an unknown error has occured.")
        