# Login / API key info
OAUTH_TOKEN = ""
USERNAME = ""
CLIENT_ID = ""
TWITCH_API_HEADERS = {"Authorization": "Bearer {}".format(OAUTH_TOKEN), "Client-ID": "{}".format(CLIENT_ID)}
WOLFRAM_APP_ID = ""
OCR_SPACE_APIKEY = ""

# Command prefix
COMMAND_PREFIX = "_"

# Do not change these!
TWITCH_DELIMITER = "\r\n"
HOST = "irc.chat.twitch.tv"
PORT = 6667

# Add the channels that you want to join here!
channels = []

# Debug channel will be the place where the bot reports once it's online.
debug_channel = ""
channels.append(debug_channel)
