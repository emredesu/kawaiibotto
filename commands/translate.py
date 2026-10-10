from commands.command import Command
import unicodedata
import requests


class TranslateCommand(Command):
	COMMAND_NAME = "translate"
	COOLDOWN = 10
	DESCRIPTION = "Translate something! Use to:(language name) and from:(language name) to specify the targets! If not specified, \"auto\" will be used for source language and English will be assumed for target language."

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
		args = messageData.content.split()
		args.pop(0)

		text_array = []

		source_language = "auto"
		target_language = "en"

		for arg in args:
			if arg.startswith("from:"):
				source_language = arg[5::]
			elif arg.startswith("to:"):
				target_language = arg[3::]
			else:
				text_array.append(arg)

		for key, value in self.google_supported_languages.items():
			if source_language.lower() == key.lower():
				source_language = self.google_supported_languages[key]
				break
			elif value == source_language.lower():
				break
		else:
			bot.send_reply_message(messageData, f"That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
			return

		for key, value in self.google_supported_languages.items():
			if key.lower() == target_language.lower():
				target_language = self.google_supported_languages[key]
				break
			elif value == target_language.lower():
				break
		else:
			bot.send_reply_message(messageData, f"That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
			return

		text = " ".join(text_array)
		data = requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={text}&ie=UTF-8&oe=UTF-8").json()
		
		translated_text = data[0][0][0]

		if source_language == "auto":
			source_language = data[2]

		bot.send_reply_message(messageData, f"{source_language} -> {target_language} - {translated_text}")


class RomanizeCommand(Command):
	COMMAND_NAME = ["romanize", "latinize", "transliterate"]
	COOLDOWN = 10
	DESCRIPTION = "Translate text and return the result in the Latin alphabet. Use to:<language> and from:<language> to specify the target and source languages."

	def execute(self, bot, messageData):
		args = messageData.content.split()[1:]
		source_language = "auto"
		target_language = "en"
		text_array = []

		for arg in args:
			if arg.startswith("from:"):
				source_language = arg[5:]
			elif arg.startswith("to:"):
				target_language = arg[3:]
			else:
				text_array.append(arg)

		if not text_array:
			bot.send_reply_message(messageData, "Usage: transliterate [from:<language>] [to:<language>] <text>")
			return

		supported_languages = {}
		for name, code in TranslateCommand.google_supported_languages.items():
			normalized_code = code.replace(" ", "")
			supported_languages[name.lower().replace(" ", "")] = normalized_code
			supported_languages[normalized_code.lower()] = normalized_code

		normalized_source = source_language.lower().replace(" ", "")
		normalized_target = target_language.lower().replace(" ", "")
		if normalized_source not in supported_languages or normalized_target not in supported_languages:
			bot.send_reply_message(messageData, "That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
			return

		source_language = supported_languages[normalized_source]
		target_language = supported_languages[normalized_target]

		text = " ".join(text_array)
		try:
			response = requests.get(
				"https://translate.googleapis.com/translate_a/single",
				params={
					"client": "gtx",
					"sl": source_language,
					"tl": target_language,
					"dt": "t",
					"q": text
				},
				timeout=10
			)
			response.raise_for_status()
			data = response.json()
		except ValueError:
			bot.send_reply_message(messageData, "The translation service returned an invalid response.")
			return
		except requests.RequestException:
			bot.send_reply_message(messageData, "The translation service is unavailable right now.")
			return

		if not isinstance(data, list) or not data or not isinstance(data[0], list):
			bot.send_reply_message(messageData, "The translation service returned an invalid response.")
			return

		translated_segments = [
			segment[0]
			for segment in data[0]
			if isinstance(segment, list)
			and segment
			and isinstance(segment[0], str)
		]
		if not translated_segments:
			bot.send_reply_message(messageData, "The translation service returned an invalid response.")
			return

		translated_text = "".join(translated_segments)
		if source_language == "auto":
			if len(data) <= 2 or not isinstance(data[2], str):
				bot.send_reply_message(messageData, "The translation service returned an invalid response.")
				return
			source_language = data[2]

		if all(not char.isalpha() or "LATIN" in unicodedata.name(char, "") for char in translated_text):
			transliterated_text = translated_text
		else:
			try:
				response = requests.get(
					"https://translate.googleapis.com/translate_a/single",
					params={
						"client": "gtx",
						"sl": target_language,
						"tl": "en",
						"dt": "rm",
						"q": translated_text
					},
					timeout=10
				)
				response.raise_for_status()
				romanization_data = response.json()
			except ValueError:
				bot.send_reply_message(messageData, "The transliteration service returned an invalid response.")
				return
			except requests.RequestException:
				bot.send_reply_message(messageData, "The transliteration service is unavailable right now.")
				return

			if not isinstance(romanization_data, list) or not romanization_data or not isinstance(romanization_data[0], list):
				bot.send_reply_message(messageData, "The transliteration service returned an invalid response.")
				return

			romanized_segments = []
			for index, segment in enumerate(romanization_data[0]):
				if isinstance(segment, list) and len(segment) > 3 and isinstance(segment[3], str) and segment[3].strip():
					romanized_segments.append(segment[3].strip())
				elif index < len(translated_segments) and all(
					not char.isalpha() or "LATIN" in unicodedata.name(char, "")
					for char in translated_segments[index]
				):
					romanized_segments.append(translated_segments[index])

			if not romanized_segments:
				bot.send_reply_message(messageData, "The transliteration service could not transliterate that text.")
				return
			transliterated_text = "".join(romanized_segments)

		bot.send_reply_message(messageData, f"{source_language} -> {target_language} - {transliterated_text}")
