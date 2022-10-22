from globals import *
from messagetypes import *
from instantiatecommands import instantiate_commands
import datetime
import socket
import time
import traceback
import threading

class kawaiibotto:
	def __init__(self):
		self.start_time = datetime.datetime.now()
		self.commands = []
		self.socket = socket.socket()

		self.last_twitch_pinged_time = None
		self.last_twitch_pong_time = None

		self.connected_once = False
		self.reconnections = 0

		instantiate_commands(self.commands)
		self.start()

	def send_message(self, ch, msg):
		if len(msg) > 500:	# can't send messages with a length of over 500 to Twitch IRC, so the bot sends them seperately if the message is larger than 500 characters
			messages = [msg[i:i+500] for i in range(0, len(msg), 500)]
			for i in messages:
				self.socket.send("PRIVMSG #{} :{}\r\n".format(ch, i.replace("\n", " ")).encode("utf-8"))
		else:
			self.socket.send("PRIVMSG #{} :{}\r\n".format(ch, msg.replace("\n", " ")).encode("utf-8"))	# irc does not accept newlines, so we replace them with spaces

	def ping_twitch(self):
		self.last_twitch_pinged_time = datetime.datetime.now()
		self.socket.send("PING :tmi.twitch.tv\r\n".encode("utf-8"))

	def connect(self):
		while True:
			try:
				self.socket.connect((HOST, PORT))
			except (socket.gaierror, socket.timeout):
				error("couldn't connect to {}. retrying in {} seconds...".format(HOST, self.reconnections ** 2))
				self.socket.close()
				self.socket = socket.socket()
				time.sleep(self.reconnections ** 2)
			else:
				self.socket.send("PASS oauth:{}\r\n".format(OAUTH_TOKEN).encode("utf-8"))
				self.socket.send("NICK {}\r\n".format(USERNAME).encode("utf-8"))
				success("connected to twitch.")

				for ch in channels:
					self.socket.send("JOIN #{}\r\n".format(ch).encode("utf-8"))
					time.sleep(0.6) # Twitch now has a 20 JOIN request limit per 10 seconds. We'll wait 0.6 seconds after every join attempt rather than 0.5 just to be safe.
					if not self.connected_once:
						log("joined {}".format(ch))

				if not self.connected_once:
					self.send_message(debug_channel, "/me {} live with {} {} connected! VoHiYo".format(USERNAME, len(channels), "channel" if len(channels) == 1 else "channels"))
					connected_once = True

				self.ping_twitch()
				break

	def reconnect(self):
		self.reconnections += 1
		wait_time = 2 ** self.reconnections
		if wait_time > 1800:
			wait_time = 1800

		error("Attempting reconnection in {} seconds...".format(wait_time))

		self.socket.close()
		self.socket = socket.socket()

		time.sleep(wait_time)

		self.connect()
	
	def parsemsg(self, msg):
		"""
		Breaks a message from an IRC server into its prefix, command, and arguments.
		"""
		prefix = ''
		trailing = []
		try:
			if msg[0] == ':':
				prefix, msg = msg[1:].split(' ', 1)
			if msg.find(' :') != -1:
				msg, trailing = msg.split(' :', 1)
				args = msg.split()
				args.append(trailing)
			else:
				args = msg.split()
			command = args.pop(0)
			return prefix, command, args
		except Exception as e:
			error(f"Error while parsing message {msg}: {e.__class__.__name__}: {str(e)}")
			return None

	def process_irc_message(self, message):
		data = self.parsemsg(message)
		data_type = data[1] if data is not None else "FAILED_TO_PARSE"

		if data_type == "PING":
			self.socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
			log("answered the twitch ping")
			self.ping_twitch() # When Twitch pings us, we ping Twitch back to get our current ping.
		elif data_type == "PONG":
			self.last_twitch_pong_time = datetime.datetime.now()
		elif data_type == "RECONNECT":
			log("Reconnecting per Twitch's demand...")
			self.reconnect()
			return
		elif data_type == "PRIVMSG":
			channel = data[2][0][1::]
			message = data[2][1]
			user = ""

			for char in data[0]:
				if char == "!":
					break
				else:
					user += char

			# Command invocation
			if message.startswith(COMMAND_PREFIX):
				invoked_command = message.split()[0][len(COMMAND_PREFIX)::]

				for command in self.commands:
					if isinstance(command.COMMAND_NAME, list):	# alias support
						for alias in command.COMMAND_NAME:
							if alias == invoked_command:
								thread = threading.Thread(target=self.execute_command, args=(command, user, message, channel)) # Spawn a new thread for the command 
								thread.start()
					else:
						if command.COMMAND_NAME == invoked_command:
							thread = threading.Thread(target=self.execute_command, args=(command, user, message, channel))
							thread.start()
			elif message.startswith("pajaVanish"):
				self.send_message(channel, f"/timeout {user} 1")

	def execute_command(self, cmnd, user, message, channel):
		if time.time() - cmnd.last_used > cmnd.COOLDOWN:  # cooldown management
			try:
				cmnd.execute(self, user, message, channel)
				log(f"{user} used {COMMAND_PREFIX}{cmnd.COMMAND_NAME} in {channel}")
				cmnd.last_used = time.time()
			except Exception as e:
				error(f"execution of command {cmnd.COMMAND_NAME} failed with {str(e.__class__.__name__)}: {str(e)}")
				self.send_message(channel, f"{user}, the execution of the command failed!")
		else:
			self.send_message(channel, f"{user}, that command is on cooldown :c")

	def start(self):
		self.connect()
		buffer = ""

		while True:
			try:
				# Implementation of receiving from a TCP buffer until a delimiter is found.
				while TWITCH_DELIMITER not in buffer:
					self.socket.settimeout(600.0)
					response = self.socket.recv(2048).decode("utf-8", "ignore")
					if not response:
						error("Disconnected from Twitch. Reconnecting...")
						self.reconnect()
						continue
					else:
						buffer += response
						self.reconnections = 0 # Reset reconnection count if we're able to receive from Twitch. (which would indicate that we're connected now)
					
				message, seperator, buffer = buffer.partition(TWITCH_DELIMITER)
				self.process_irc_message(message)
			except Exception as e:
				error(f"Failed to recv from Twitch, exception: {e.__class__.__name__}")
				error(f"Printing traceback: ")
				traceback.print_exc()

				log("Attempting reconnection.")
				self.reconnect()
				continue

if __name__ == "__main__":
	bot = kawaiibotto()
