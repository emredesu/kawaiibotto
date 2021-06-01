from globals import *
from messagetypes import *
from instantiatecommands import instantiate_commands
import datetime
import socket
import re
import time
import traceback

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
			s.send("PRIVMSG #{} :{}\r\n".format(ch, msg.replace("\n", " ")).encode("utf-8"))  # irc does not accept newlines, so we replace them with spaces

	def connect(self):
		global s, connected_once
		while True:
			try:
				s.connect((HOST, PORT))
			except (socket.gaierror, socket.timeout):
				error("couldn't connect to {}. retrying in {} seconds...".format(HOST, reconnections ** 2))
				s.close()
				s = socket.socket()
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
		wait_time = 2 ** reconnections
		if wait_time > 1800:
			wait_time = 1800

		error("Attempting reconnection in {} seconds...".format(wait_time))

		s.close()
		s = socket.socket()

		time.sleep(wait_time)

		bot.connect()
		reconnections = 0
	
	@staticmethod
	def parsemsg(s):
		"""
		Breaks a message from an IRC server into its prefix, command, and arguments.
		"""
		prefix = ''
		trailing = []
		try:
			if s[0] == ':':
				prefix, s = s[1:].split(' ', 1)
			if s.find(' :') != -1:
				s, trailing = s.split(' :', 1)
				args = s.split()
				args.append(trailing)
			else:
				args = s.split()
			command = args.pop(0)
			return prefix, command, args
		except Exception as e:
			error(f"Error while parsing message {s}: {str(e.__class__.__name__)}: {str(e)}")
			return None

	@staticmethod
	def execute_command(cmnd):
		if time.time() - cmnd.last_used > cmnd.COOLDOWN:  # cooldown management
			try:
				cmnd.execute(bot, user, message, channel)
				log(f"{user} used {COMMAND_PREFIX}{invoked_command} in {channel}")
				cmnd.last_used = time.time()
			except Exception as e:
				error(f"execution of command {cmnd.COMMAND_NAME} failed with {str(e.__class__.__name__)}: {str(e)}")
				bot.send_message(channel, f"{user}, the execution of that command failed! Sorry for the inconvenience, it will be fixed soon hopefully ;w;")
		else:
			bot.send_message(channel, f"{user}, that command is on cooldown :c")


if __name__ == "__main__":
	bot = kawaiibotto()

	while True:
		try:
			response = s.recv(2048).decode("utf-8", "ignore")
			if not response:
				error("Disconnected from Twitch. Reconnecting...")
				bot.reconnect()
		except Exception as e:
			error(f"Failed to recv from Twitch, exception: {e.__class__.__name__}")
			error(f"Printing traceback: ")
			traceback.print_exc()

			log("Attempting reconnection.")
			bot.reconnect()
			continue

		data = bot.parsemsg(response)
		data_type = data[1] if data is not None else "FAILED_TO_PARSE"

		if data_type == "PING":
			s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
			log("answered the twitch ping")
		elif data_type == "RECONNECT":
			time.sleep(60)
			bot.reconnect()
		elif data_type == "PRIVMSG":
			channel = data[2][0][1::]
			message = data[2][1]
			user = ""

			for char in data[0]:
				if char == "!":
					break
				else:
					user += char

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