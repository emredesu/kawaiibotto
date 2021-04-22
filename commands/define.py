from commands.command import Command
import requests

class DefineCommand(Command):
    COMMAND_NAME = ["define", "definion", "dictionary"]
    COOLDOWN = 10

    supported_language_codes = ["en_US", "hi", "es", "fr", "ja", "ru", "en_GB", "de", "it", "ko", "pt-BR", "ar", "tr"]

    def execute(self, bot, user, message, channel):
        args = message.split()
        args.pop(0)

        target_word = None
        target_language = None
        target_index = 0

        if len(args) < 1:
            bot.send_message(channel, "Inadequate amount of parameters supplied! Example usage: _define cute lang:en")
            return

        for arg in args:
            if arg.startswith("lang:"):
                requested_target_language = arg[5::]
                args.remove(arg)

                if requested_target_language.lower() == "en":
                    target_language = "en_US"
                    break

                if requested_target_language not in self.supported_language_codes:
                    bot.send_message(channel, f"{requested_target_language} is not a supported language code. Supported language codes are: {' '.join(self.supported_language_codes)}")
                    return

                target_language = requested_target_language
                break
            elif arg.startswith("index:"):
                try:
                    requested_index = int(arg[6::])
                    target_index = requested_index
                    args.remove(arg)
                except ValueError:
                    bot.send_message(channel, "An invalid value (non-int) was supplied after \"index:\"!")
                    return
        
        if target_language is None:
            target_language = "en_US"

        target_word = args[0]

        api_request = f"https://api.dictionaryapi.dev/api/v2/entries/{target_language}/{target_word}"
        result = requests.get(api_request)

        if result.status_code != 200:
            bot.send_message(channel, f"{user}, {result.json()['message']}")
            return

        try:
            result = result.json()
        except json.decoder.JSONDecodeError:
            bot.send_message(channel, "There was an error getting the definiton for that word. Try again later.")
            return

        data = result[0]
        data_max_index = len(data["meanings"]) - 1

        if target_index > data_max_index:
            bot.send_message(channel, f"Requested index is too big! Max index for this query is {data_max_index}.")
            return

        part_of_speech = data["meanings"][target_index]["partOfSpeech"]
        definition = data["meanings"][target_index]["definitions"][0]["definition"]
        example_usage = None
        try:
            example_usage = data["meanings"][target_index]["definitions"][0]["example"]
        except KeyError:
            example_usage = "(NOT FOUND)"
        
        to_send = f"index ({target_index}/{data_max_index}) {target_word} ({part_of_speech}): {definition} Example usage: {example_usage}"

        bot.send_message(channel, to_send)