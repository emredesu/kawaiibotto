from globals import *
from messagetypes import *
from instantiatecommands import instantiate_commands, instantiate_whisper_commands
from messageParser import TwitchIRCMessage
import datetime
import socket
import time
import traceback
import threading
import requests
import json

class kawaiibotto:
	def __init__(self):
		self.start_time = datetime.datetime.now()
		self.commands = []
		self.whisperCommands = []
		self.socket = socket.socket()

		self.last_twitch_pinged_time = None
		self.last_twitch_pong_time = None

		self.connected_once = False
		self.reconnections = 0

		instantiate_commands(self.commands)
		instantiate_whisper_commands(self.whisperCommands)
		self.start()

	def send_message(self, ch, msg):
		if len(msg) > 500:	# can't send messages with a length of over 500 to Twitch IRC, so the bot sends them seperately if the message is larger than 500 characters
			messages = [msg[i:i+500] for i in range(0, len(msg), 500)]
			for i in messages:
				self.socket.send("PRIVMSG #{} :{}\r\n".format(ch, i.replace("\n", " ")).encode("utf-8"))
		else:
			self.socket.send("PRIVMSG #{} :{}\r\n".format(ch, msg.replace("\n", " ")).encode("utf-8"))	# irc does not accept newlines, so we replace them with spaces

	def send_whisper(self, messageDataFromWhisper, msg):
		if len(msg) > 500:	# can't send messages with a length of over 500 to Twitch IRC, so the bot sends them seperately if the message is larger than 500 characters
			msg = msg[480] + "..."
		
		requests.post(f"https://api.twitch.tv/helix/whispers?from_user_id={TWITCH_BOT_UID}&to_user_id={messageDataFromWhisper.tags['user-id']}", headers=TWITCH_API_WHISPER_HEADERS, data=json.dumps({"message": f"{msg}"}))

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
				self.socket.send("CAP REQ :twitch.tv/commands twitch.tv/tags\r\n".encode("utf-8")) # Request message tags capabilities
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
	
	def ParseMessage(self, msg) -> TwitchIRCMessage:
		return TwitchIRCMessage(msg)

	def process_irc_message(self, rawMessage):
		parsedMsg = self.ParseMessage(rawMessage)

		if parsedMsg.messageType == "PING":
			self.socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
			self.ping_twitch() # When Twitch pings us, we ping Twitch back to get our current RTT to Twitch servers.
		elif parsedMsg.messageType == "PONG":
			self.last_twitch_pong_time = datetime.datetime.now()
		elif parsedMsg.messageType == "RECONNECT":
			log("Reconnecting per Twitch's demand...")
			self.reconnect()
			return
		elif parsedMsg.messageType == "PRIVMSG":
			# Command invocation
			if parsedMsg.content.startswith(COMMAND_PREFIX):
				invoked_command = parsedMsg.content.split()[0][len(COMMAND_PREFIX)::]

				for command in self.commands:
					if isinstance(command.COMMAND_NAME, list): # alias support
						for alias in command.COMMAND_NAME:
							if alias == invoked_command:
								if self.CheckCanExecute(command, parsedMsg.user):
									self.execute_command(command, parsedMsg)
					else:
						if command.COMMAND_NAME == invoked_command:
							if self.CheckCanExecute(command, parsedMsg.user):
								self.execute_command(command, parsedMsg)
		elif parsedMsg.messageType == "WHISPER":
			# Whisper command invocation
			if parsedMsg.whisperContent.startswith(COMMAND_PREFIX):
				invoked_command = parsedMsg.whisperContent.split()[0][len(COMMAND_PREFIX)::]

				for command in self.whisperCommands:
					if isinstance(command.COMMAND_NAME, list): # alias support
						for alias in command.COMMAND_NAME:
							if alias == invoked_command:
								if self.CheckCanExecute(command, parsedMsg.user):
									self.execute_command(command, parsedMsg)
					else:
						if command.COMMAND_NAME == invoked_command:
							if self.CheckCanExecute(command, parsedMsg.user):
								self.execute_command(command, parsedMsg)

	def CheckCanExecute(self, cmnd, user) -> bool:
		if user in cmnd.lastUseTimePerUser:
			if time.time() - cmnd.lastUseTimePerUser[user] > cmnd.COOLDOWN:
				return True
			else:
				return False
		else:
			return True

	def execute_command(self, cmnd, messageData):
		cmnd.lastUseTimePerUser[messageData.user] = time.time()

		try:
			cmnd.execute(self, messageData)
			if messageData.messageType != "WHISPER":
				log(f"{messageData.user} used {COMMAND_PREFIX}{cmnd.COMMAND_NAME} in {messageData.channel}")
			else:
				log(f"{messageData.whisperUser} used {COMMAND_PREFIX}{cmnd.COMMAND_NAME} through whispers. Full message: {messageData.whisperContent}")
		except Exception as e:
			error(f"execution of command {cmnd.COMMAND_NAME} failed with {str(e.__class__.__name__)}: {str(e)}")
			self.send_message(messageData.channel, f"{messageData.user}, the execution of that command failed! The error has been logged, and will be fixed soon.")

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
