from datetime import datetime

has_colorama = None

try:
	import colorama
	has_colorama = True
	colorama.init()
except ModuleNotFoundError:
	has_colorama = False


def time_now():
	now = datetime.now()
	return now.strftime("%d/%m/%Y %H:%M:%S")


def error(string):
	if has_colorama:
		print(colorama.Fore.RED + ("{} [ERROR] ".format(time_now()) + string))
	else:
		print("{} [ERROR] ".format(time_now()) + string)


def success(string):
	if has_colorama:
		print(colorama.Fore.GREEN + ("{} [SUCCESS] ".format(time_now()) + string))
	else:
		print("{} [SUCCESS] ".format(time_now()) + string)


def log(string):
	if has_colorama:
		print(colorama.Fore.BLUE + ("{} [LOG] ".format(time_now()) + string))
	else:
		print("{} [LOG] ".format(time_now()) + string)
