from commands.command import Command
from decimal import Decimal, InvalidOperation
import math
import requests

class CurrencyCommand(Command):
	COMMAND_NAME = "currency"
	COOLDOWN = 5
	DESCRIPTION = "Convert currencies. Usage: _currency <amount> <from_currency> to <to_currency> (example: _currency 100 usd to try)."
	usage = "Example: _currency 100 USD to TRY"

	def execute(self, bot, messageData):
		args = messageData.content.split()

		if len(args) != 5 or args[3].lower() != "to":
			bot.send_reply_message(messageData, self.usage)
			return

		try:
			amount = Decimal(args[1])
		except InvalidOperation:
			bot.send_reply_message(messageData, f"Amount must be a positive number. {self.usage}")
			return

		if not amount.is_finite() or amount <= 0:
			bot.send_reply_message(messageData, f"Amount must be a positive number. {self.usage}")
			return

		from_currency = args[2].upper()
		to_currency = args[4].upper()
		if not from_currency.isascii() or not from_currency.isalpha() or len(from_currency) != 3 \
				or not to_currency.isascii() or not to_currency.isalpha() or len(to_currency) != 3:
			bot.send_reply_message(messageData, f"Currency codes must be three-letter ISO currency codes. {self.usage}")
			return

		try:
			response = requests.get(
				"https://api.frankfurter.app/latest",
				params={
					"amount": format(amount, "f"),
					"from": from_currency,
					"to": to_currency,
				},
				timeout=10,
			)
			if response.status_code == 404:
				bot.send_reply_message(messageData, f"One or both currency codes are not supported. {self.usage}")
				return
			response.raise_for_status()
			data = response.json()
		except requests.exceptions.Timeout:
			bot.send_reply_message(messageData, "Currency conversion timed out. Please try again later.")
			return
		except ValueError:
			bot.send_reply_message(messageData, "Currency conversion service returned an invalid response.")
			return
		except requests.exceptions.RequestException:
			bot.send_reply_message(messageData, "Currency conversion service is unavailable. Please try again later.")
			return

		if not isinstance(data, dict) or not isinstance(data.get("rates"), dict):
			bot.send_reply_message(messageData, "Currency conversion service returned an invalid response.")
			return

		converted_amount = data["rates"].get(to_currency)
		if not isinstance(converted_amount, (int, float)) or isinstance(converted_amount, bool) \
				or not math.isfinite(converted_amount):
			bot.send_reply_message(messageData, f"One or both currency codes are not supported. {self.usage}")
			return

		bot.send_reply_message(
			messageData,
			f"{format(amount, 'f')} {from_currency} = {converted_amount:,.2f} {to_currency}",
		)