from commands.command import Command
import pytesseract
from PIL import Image, UnidentifiedImageError
import requests

class OCRCommand(Command):
    COMMAND_NAME = "ocr"
    COOLDOWN = 30
    DESCRIPTION = "Use OCR (optical character recognition) to extract the text from an image link. You can specify the language" \
                "using \"lang:(language code here)\". Example usage: _ocr https://i.nuuls.com/leMKr.png lang:jpn"

    def execute(self, bot, user, message, channel):
        available_languages = pytesseract.get_languages(config="")
        target_language = "eng"

        message_args = message.split()
        message_args.pop(0) # Get rid of the first arg that's used to invoke the command.
        for arg in message_args:
            if arg.startswith("lang:"):
                target_language = arg[5:]
                message_args.remove(arg)

        if target_language not in pytesseract.get_languages(config=""):
            bot.send_message(channel, f"{user}, {target_language} is not a supported language code! Find the language code for your " \
                                     "language from here: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html")
            return

        try:
            request = requests.get(message_args[0], stream=True)
            if request.status_code != 200:
                bot.send_message(channel, f"{user}, failed to connect, the website returned {request.status_code}")
                return

            image = Image.open(request.raw)
            result = pytesseract.image_to_string(image, lang=target_language)

            bot.send_message(channel, f"{user}, {result}")
        except requests.ConnectionError:
            bot.send_message(channel, f"{user}, connection failed.")
            return
        except requests.HTTPError:
            bot.send_message(channel, f"{user}, invalid HTTP response received.")
            return
        except requests.Timeout:
            bot.send_message(channel, f"{user}, GET request timed out.")
            return
        except UnidentifiedImageError:
            bot.send_message(channel, f"{user}, this image cannot be opened and identified.")
            return
        except Image.DecompressionBombError:
            bot.send_message(channel, f"{user}, that image exceeds the file size limit. Are you trying to DOS me? 🤨")
            return
        except (ValueError, TypeError):
            bot.send_message(channel, f"{user}, either the link you gave returns data that cannot be parsed into the required raw byte " \
                                        "format or you just didn't give a valid link.")
            return
        except pytesseract.pytesseract.TesseractNotFoundError:
            bot.send_message(channel, f"{user}, this instance of kawaiibotto does not have Tesseract set up in its environment.")
            return
        except pytesseract.pytesseract.TesseractError:
            bot.send_message(channel, f"{user}, there was an error with the OCR engine.")