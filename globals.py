# Login info
OAUTH_TOKEN = ""
USERNAME = ""
CLIENT_ID = ""
TWITCH_API_HEADERS = {"Authorization": "Bearer {}".format(OAUTH_TOKEN), "Client-ID": "{}".format(CLIENT_ID)}
TWITCH_API_WHISPER_HEADERS = {"Authorization": "Bearer {}".format(OAUTH_TOKEN), "Client-ID": "{}".format(CLIENT_ID), "Content-Type": "application/json"}
TWITCH_BOT_UID = 0 # Required for whispers functionality.

# API key info for various apps
WOLFRAM_APP_ID = ""
OCR_SPACE_APIKEY = ""
OPENAI_APIKEY = ""
GOOGLE_GEMINI_APIKEY = ""

# Genshin command specific values
GENSHIN_MYSQL_DB_HOST = "192.168.1.1"
GENSHIN_MYSQL_DB_USERNAME = ""
GENSHIN_MYSQL_DB_PASSWORD = ""
GENSHIN_DB_POOL_SIZE = 25

# HoyoLAB cookies for Hoyoverse game command data
kawaiibottoHoyolabCookies = {"ltuid_v2": 0, "ltoken_v2": "", "ltmid_v2": ""}
kawaiibottoGenshinUID = 0
kawaiibottoStarRailUID = 0

# Platform values
SUDO_PASSWORD = ""

# Command prefix
COMMAND_PREFIX = "_"

# Do not change these!
TWITCH_DELIMITER = "\r\n"
HOST = "irc.chat.twitch.tv"
PORT = 6667

# Add the channels that you want to join here! (make sure the names are all in lower case)
channels = []

# Debug channel will be the place where the bot reports once it's online.
debug_channel = ""
channels.append(debug_channel)

# Authorized user that will have more control over some commands.
AUTHORIZED_USER = ""
