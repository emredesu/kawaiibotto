
# Login / API key info
OAUTH_TOKEN = ""
USERNAME = ""
CLIENT_ID = ""
TWITCH_API_HEADERS = {"Authorization": "Bearer {}".format(OAUTH_TOKEN), "Client-ID": "{}".format(CLIENT_ID)}
WOLFRAM_APP_ID = ""
OCR_SPACE_APIKEY = ""
OPENAI_APIKEY = ""
GENSHIN_COOKIES = {'ltoken': '', 'ltuid': '', 'account_mid_v2': '', 'cookie_token_v2': ''}

# Genshin command specific values
GENSHIN_MYSQL_DB_HOST = ""
GENSHIN_MYSQL_DB_USERNAME = ""
GENSHIN_MYSQL_DB_PASSWORD = ""

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
