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

class OCRTranslateCommand(Command):
    COMMAND_NAME = ["ocrtranslate", "ocrt"]
    COOLDOWN = 10
    DESCRIPTION = "Use OCR (optical character recognition) to extract the text from an image link, and then translate the extracted text to a target language. Example usage: _ocrt https://kappa.lol/xCwZo from:tr to:en"

    # A dictionary that converts full language names and two letter codes into three letter codes.
    matchedLanguageCodesForOCR = {
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

    google_supported_languages = {
        "Afrikaans": "af",
        "Albanian":	"sq",
        "Amharic": "am",
        "Arabic": "ar",
        "Armenian": "hy",
        "Azerbaijani": "az",
        "Basque": "eu",
        "Belarusian": "be",
        "Bengali": "bn",
        "Bosnian": "bs",
        "Bulgarian": "bg",
        "Catalan": "ca",
        "Cbuano": "ceb",
        "Chinese(Simplified)": "zh",
        "Chinese(Traditional)":	"zh - TW",
        "Corsican":	"co",
        "Croatian": "hr",
        "Czech": "cs",
        "Danish": "da",
        "Dutch": "nl",
        "English": "en",
        "Esperanto": "eo",
        "Estonian": "et",
        "Finnish": "fi",
        "French": "fr",
        "Frisian": "fy",
        "Galician": "gl",
        "Georgian": "ka",
        "German": "de",
        "Greek": "el",
        "Gujarati": "gu",
        "Haitian_Creole": "ht",
        "Hausa": "ha",
        "Hawaiian": "haw",
        "Hebrew": "he",
        "Hindi": "hi",
        "Hmong": "hmn",
        "Hungarian": "hu",
        "Icelandic": "is",
        "Igbo": "ig",
        "Indonesian": "id",
        "Irish": "ga",
        "Italian": "it",
        "Japanese": "ja",
        "Javanese": "jv",
        "Kannada": "kn",
        "Kazakh": "kk",
        "Khmer": "km",
        "Kinyarwanda": "rw",
        "Korean": "ko",
        "Kurdish": "ku",
        "Kyrgyz": "ky",
        "Lao": "lo",
        "Latin": "la",
        "Latvian": "lv",
        "Lithuanian": "lt",
        "Luxembourgish": "lb",
        "Macedonian": "mk",
        "Malagasy": "mg",
        "Malay": "ms",
        "Malayalam": "ml",
        "Maltese": "mt",
        "Maori": "mi",
        "Marathi": "mr",
        "Mongolian": "mn",
        "Myanmar": "my",
        "Burmese": "my",
        "Nepali": "ne",
        "Norwegian": "no",
        "Nyanja": "ny",
        "Chichewa": "ny",
        "Odia": "or",
        "Oriya": "or",
        "Pashto": "ps",
        "Persian": "fa",
        "Polish": "pl",
        "Portuguese": "pt",
        "Punjabi": "pa",
        "Romanian": "ro",
        "Russian": "ru",
        "Samoan": "sm",
        "Scots_Gaelic": "gd",
        "Serbian": "sr",
        "Sesotho": "st",
        "Shona": "sn",
        "Sindhi": "sd",
        "Sinhala": "si",
        "Sinhalese": "si",
        "Slovak": "sk",
        "Slovenian": "sl",
        "Somali": "so",
        "Spanish": "es",
        "Sundanese": "su",
        "Swahili": "sw",
        "Swedish": "sv",
        "Tagalog": "tl",
        "Filipino": "tl",
        "Tajik": "tg",
        "Tamil": "ta",
        "Tatar": "tt",
        "Telugu": "te",
        "Thai": "th",
        "Turkish": "tr",
        "Turkmen": "tk",
        "Ukrainian": "uk",
        "Urdu": "ur",
        "Uyghur": "ug",
        "Uzbek": "uz",
        "Vietnamese": "vi",
        "Welsh": "cy",
        "Xhosa": "xh",
        "Yiddish": "yi",
        "Yoruba": "yo",
        "Zulu": "zu",
        "auto": "auto"
    }

    def execute(self, bot, messageData):
        textLanguage = "eng"
        targetLanguage = "en"

        textArray = []

        message_args = messageData.content.split()
        message_args.pop(0) # Get rid of the first arg that's used to invoke the command.
        for arg in reversed(message_args):
            if arg.startswith("lang:") or arg.startswith("from:"):
                textLanguage = arg[5:]
                message_args.remove(arg)
            elif arg.startswith("to:"):
                targetLanguage = arg[3:]
                message_args.remove(arg)
            else:
                textArray.append(arg)

        print(f"{textLanguage} {targetLanguage}")

        validLanguageCodes = ["ara", "bul", "chs", "cht", "hrv", "cze", "dan", "dut", "eng", "fin", "fre", "ger", "gre", "hun", "kor", "ita", "jpn", "pol", "por", "rus", "slv", "spa", "swe", "tur"]

        # Check if the user has inputted a valid language code. If not, try to match it with a commonly used language code. 
        if textLanguage not in validLanguageCodes:
            try:
                textLanguage = self.matchedLanguageCodesForOCR[textLanguage]
            except KeyError:
                bot.send_message(messageData.channel, f"{messageData.user}, the language code you inputted is invalid. Valid codes can be found at: https://ocr.space/OCRAPI#:~:text=faster%20upload%20speeds.-,language,-%5BOptional%5D%0AArabic")
                return
            
        # Check if requested target language is supported by Google API
        for key, value in self.google_supported_languages.items():
            if key.lower() == targetLanguage.lower():
                targetLanguage = self.google_supported_languages[key]
                break
            elif value == targetLanguage.lower():
                break
        else:
            bot.send_message(messageData.channel, f"{messageData.user}, That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
            return

        targetRequest = f"https://api.ocr.space/parse/imageurl?apikey={OCR_SPACE_APIKEY}&url={message_args[0]}"
        if textLanguage != "eng":
            targetRequest += f"&language={textLanguage}"

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
                    data = requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={targetLanguage}&dt=t&q={parsedText}&ie=UTF-8&oe=UTF-8").json()
                    is_successful = bool(data[0][0][4])

                    if not is_successful:
                        bot.send_message(messageData.channel, f"{messageData.user}, translation failed ;w;")
                        return
                    else:
                        translated_text = ""
                        for i in range(len(data[0])):
                            translated_text += data[0][i][0]

                        bot.send_message(messageData.channel, f"{messageData.user}, {data[2]} -> {targetLanguage} - {translated_text}")
        except:
            bot.send_message(messageData.channel, f"{messageData.user}, an unknown error has occured.")
