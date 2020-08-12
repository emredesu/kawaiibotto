from globals import *
from messagetypes import *
from instantiatecommands import instantiate_commands
import datetime
import socket
import re
import time

s = socket.socket()
connected_once = False
reconnections = 0


class kawaiibotto:
	def __init__(self):
		self.connect()
		self.start_time = datetime.datetime.now()
		self.commands = []
		instantiate_commands(self.commands)

	@staticmethod
	def send_message(ch, msg):
		if len(msg) > 500:  # can't send messages with a length of over 500 to Twitch IRC, so the bot sends them seperately if the message is larger than 500 characters
			messages = [msg[i:i+500] for i in range(0, len(msg), 500)]
			for i in messages:
				s.send("PRIVMSG #{} :{}\r\n".format(ch, i).encode("utf-8"))
		else:
			s.send("PRIVMSG #{} :{}\r\n".format(ch, msg).encode("utf-8"))

	def connect(self):
		global s, connected_once
		while True:
			try:
				s.connect((HOST, PORT))
			except socket.gaierror or socket.timeout:
				error("couldn't connect to {}. retrying in {} seconds...".format(HOST, reconnections ** 2))
				s.close()
				time.sleep(reconnections ** 2)
			else:
				s.send("PASS oauth:{}\r\n".format(OAUTH_TOKEN).encode("utf-8"))
				s.send("NICK {}\r\n".format(USERNAME).encode("utf-8"))
				success("connected to twitch.")

				for ch in channels:
					s.send("JOIN #{}\r\n".format(ch).encode("utf-8"))
					if not connected_once:
						log("joined {}".format(ch))

				if not connected_once:
					self.send_message(debug_channel, "/me {} live with {} {} connected! VoHiYo".format(USERNAME, len(channels), "channel" if len(channels) == 1 else "channels"))
					connected_once = True

				break

	@staticmethod
	def reconnect():
		global s, reconnections
		reconnections += 1
		error("disconnected from twitch. attempting to reconnect in {} seconds...".format(2 ** reconnections))
		s.close()
		time.sleep(2 ** reconnections)
		s = socket.socket()
		bot.connect()

	@staticmethod
	def execute_command(cmnd):
		if time.time() - cmnd.last_used > cmnd.COOLDOWN:  # cooldown management
			cmnd.execute(bot, user, message, channel)
			log(f"{user} used {COMMAND_PREFIX}{invoked_command} in {channel}")
			cmnd.last_used = time.time()
		else:
			bot.send_message(channel, f"{user}, that command is on cooldown :c")


bot = kawaiibotto()

while True:
	response = s.recv(2048).decode("utf-8", "ignore")

	if "PING :tmi.twitch.tv\r\n" in response:
		s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
		log("answered the twitch ping")

	if "Login authentication failed" in response:
		error("oauth expired, attempting to get a new oauth...")
		# todo: get another oauth automatically

	if not response:
		bot.reconnect()

	# command handling
	try:
		user, channel, message = re.search(':(.*)!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*) :(.*)', response).groups()

		if message.startswith(COMMAND_PREFIX):
			invoked_command = message.split()[0][len(COMMAND_PREFIX)::]

			for command in bot.commands:
				if isinstance(command.COMMAND_NAME, list):  # alias support
					for alias in command.COMMAND_NAME:
						if alias == invoked_command:
							bot.execute_command(command)
				else:
					if command.COMMAND_NAME == invoked_command:
						bot.execute_command(command)
	except AttributeError:
		pass
	except KeyboardInterrupt:
		exit()
