from commands.command import Command
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
			bot.send_message(messageData.channel, f"{messageData.user}, That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
			return

		for key, value in self.google_supported_languages.items():
			if key.lower() == target_language.lower():
				target_language = self.google_supported_languages[key]
				break
			elif value == target_language.lower():
				break
		else:
			bot.send_message(messageData.channel, f"{messageData.user}, That language is not supported by Google translate API! To see which languages are supported, visit: https://cloud.google.com/translate/docs/languages")
			return

		text = " ".join(text_array)
		data = requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={text}&ie=UTF-8&oe=UTF-8").json()
		is_successful = bool(data[0][0][4])

		if not is_successful:
			bot.send_message(messageData.channel, f"{messageData.user}, translation failed ;w;")
			return
		else:
			translated_text = ""
			for i in range(len(data[0])):
				translated_text += data[0][i][0]

			if source_language == "auto":
				source_language = data[2]

			bot.send_message(messageData.channel, f"{messageData.user}, {source_language} -> {target_language} - {translated_text}")
