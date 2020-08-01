OAUTH_TOKEN = ""
USERNAME = ""
CLIENT_ID = ""
TWITCH_API_HEADERS = {"Authorization": "Bearer {}".format(OAUTH_TOKEN), "Client-ID": "{}".format(CLIENT_ID)}
WOLFRAM_APP_ID = ""
COMMAND_PREFIX = "_"


channels = []

debug_channel = ""
channels.append(debug_channel)

HOST = "irc.chat.twitch.tv"
PORT = 6667
