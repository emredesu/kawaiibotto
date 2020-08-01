import colorama
from datetime import datetime

colorama.init()


def time_now():
	now = datetime.now()
	return "[{}:{}:{}]".format(now.hour, "0" + str(now.minute) if len(str(now.minute)) == 1 else now.minute, "0" + str(now.second) if len(str(now.second)) == 1 else now.second)


def error(string):
	print(colorama.Fore.RED + ("{} [ERROR] ".format(time_now()) + string))


def success(string):
	print(colorama.Fore.GREEN + ("{} [SUCCESS] ".format(time_now()) + string))


def log(string):
	print(colorama.Fore.BLUE + ("{} [LOG] ".format(time_now()) + string))
