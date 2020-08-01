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
commands = []


class kawaiibotto:
	def __init__(self):
		self.connect()
		self.start_time = datetime.datetime.now()
		instantiate_commands(commands)

	@staticmethod
	def send_message(ch, msg):
		if len(msg) > 500:
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

			if invoked_command == "help":
				try:
					command_to_get_help_for = message.split()[1]
				except IndexError:
					bot.send_message(channel, "Usage: _help {command name}")
				else:
					command_found = False

					for cmd in commands:
						if cmd.COMMAND_NAME == command_to_get_help_for:
							bot.send_message(channel, cmd.DESCRIPTION)
							command_found = True

					if command_found is False:
						bot.send_message(channel, "specified command was not found ;w;")
			else:
				for command in commands:
					if command.COMMAND_NAME == invoked_command:
						if time.time() - command.last_used > command.COOLDOWN:  # cooldown management
							command.execute(bot, user, message, channel)
							log(f"{user} used {COMMAND_PREFIX}{invoked_command} in {channel}")
							command.last_used = time.time()
						else:
							bot.send_message(channel, f"{user}, that command is on cooldown :c")
	except AttributeError:
		pass
	except KeyboardInterrupt:
		exit()
