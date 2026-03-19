from commands.command import Command
import os
import platform
import time


def _format_bytes(byte_count):
	value = float(byte_count)
	units = ["B", "KB", "MB", "GB", "TB", "PB"]
	unit_index = 0

	while value >= 1024 and unit_index < len(units) - 1:
		value /= 1024
		unit_index += 1

	return f"{value:.1f}{units[unit_index]}"


def _read_proc_stat():
	with open("/proc/stat", "r", encoding="utf-8") as proc_stat_file:
		cpu_values = [int(value) for value in proc_stat_file.readline().split()[1:]]

	idle_time = cpu_values[3] + (cpu_values[4] if len(cpu_values) > 4 else 0)
	total_time = sum(cpu_values)

	return idle_time, total_time


def _get_cpu_usage_percentage(sample_duration=0.2):
	idle_time_before, total_time_before = _read_proc_stat()
	time.sleep(sample_duration)
	idle_time_after, total_time_after = _read_proc_stat()

	idle_delta = idle_time_after - idle_time_before
	total_delta = total_time_after - total_time_before

	if total_delta <= 0:
		return 0.0

	used_delta = total_delta - idle_delta
	return max(0.0, min(100.0, (used_delta / total_delta) * 100.0))


def _read_meminfo():
	meminfo = {}

	with open("/proc/meminfo", "r", encoding="utf-8") as meminfo_file:
		for line in meminfo_file:
			key, value = line.split(":", 1)
			meminfo[key] = int(value.strip().split()[0]) * 1024

	return meminfo


def _get_memory_usage(meminfo):
	total_memory = meminfo.get("MemTotal", 0)
	available_memory = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
	used_memory = max(total_memory - available_memory, 0)
	memory_usage_percentage = (used_memory / total_memory) * 100.0 if total_memory > 0 else 0.0

	return used_memory, total_memory, memory_usage_percentage


def _get_swap_usage(meminfo):
	total_swap = meminfo.get("SwapTotal", 0)
	free_swap = meminfo.get("SwapFree", 0)
	used_swap = max(total_swap - free_swap, 0)
	swap_usage_percentage = (used_swap / total_swap) * 100.0 if total_swap > 0 else 0.0

	return used_swap, total_swap, swap_usage_percentage


def _get_storage_usage(path="/"):
	storage_stats = os.statvfs(path)
	total_storage = storage_stats.f_frsize * storage_stats.f_blocks
	available_storage = storage_stats.f_frsize * storage_stats.f_bavail
	used_storage = max(total_storage - available_storage, 0)
	storage_usage_percentage = (used_storage / total_storage) * 100.0 if total_storage > 0 else 0.0

	return used_storage, total_storage, storage_usage_percentage


def _get_load_average():
	try:
		load_1m, load_5m, load_15m = os.getloadavg()
		return f"{load_1m:.2f}/{load_5m:.2f}/{load_15m:.2f}"
	except (AttributeError, OSError):
		return "N/A"


class SystemUsageCommand(Command):
	COMMAND_NAME = ["sysusage", "systemusage", "usage", "status"]
	COOLDOWN = 5
	DESCRIPTION = "Shows Linux system usage: CPU, RAM, storage, Twitch latency, swap and load average."

	def execute(self, bot, messageData):
		if platform.system() != "Linux":
			bot.send_reply_message(messageData, "This command is configured to work with Linux only.")
			return

		ping_to_twitch = (
			(bot.last_twitch_pong_time - bot.last_twitch_pinged_time).microseconds // 1000
			if bot.last_twitch_pong_time is not None and bot.last_twitch_pinged_time is not None
			else "N/A"
		)

		try:
			cpu_usage_percentage = _get_cpu_usage_percentage()
			meminfo = _read_meminfo()
			used_memory, total_memory, memory_usage_percentage = _get_memory_usage(meminfo)
			used_swap, total_swap, swap_usage_percentage = _get_swap_usage(meminfo)
			used_storage, total_storage, storage_usage_percentage = _get_storage_usage("/")
			load_average = _get_load_average()
		except OSError:
			bot.send_reply_message(messageData, "Could not read Linux system metrics from this host.")
			return

		swap_segment = (
			f" 🔁 Swap: {_format_bytes(used_swap)}/{_format_bytes(total_swap)} ({swap_usage_percentage:.1f}%)"
			if total_swap > 0
			else " 🔁 Swap: N/A"
		)

		latency_text = f"{ping_to_twitch}ms" if ping_to_twitch != "N/A" else "N/A"

		bot.send_reply_message(
			messageData,
			f"🖥️ CPU: {cpu_usage_percentage:.1f}% 🧠 RAM: {_format_bytes(used_memory)}/{_format_bytes(total_memory)} ({memory_usage_percentage:.1f}%) "
			f"💾 Storage: {_format_bytes(used_storage)}/{_format_bytes(total_storage)} ({storage_usage_percentage:.1f}%) "
			f"📡 Latency: {latency_text} 📈 Load: {load_average}{swap_segment}"
		)

		bot.ping_twitch()