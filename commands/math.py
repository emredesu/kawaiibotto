from commands.command import Command
import math
import ast
import operator
import multiprocessing.pool
from multiprocessing.context import TimeoutError


class MathCommand(Command):
	COMMAND_NAME = ["math", "calculate", "eval", "evaluate"]
	COOLDOWN = 5
	DESCRIPTION = "Do maths! To use special functions, for example square root, use sqrt(number). Your evaluation will be cancelled if its calculation takes more than 5 seconds."

	binOps = {
		ast.Add: operator.add,
		ast.Sub: operator.sub,
		ast.Mult: operator.mul,
		ast.Mod: operator.mod,
		ast.Pow: operator.pow,
		ast.Div: operator.truediv
	}

	callOps = {
		"sqrt": math.sqrt,
		"sin": math.sin,
		"cos": math.cos,
		"tan": math.tan,
		"log": math.log,
		"log10": math.log10,
		"radians": math.radians,
		"degrees": math.degrees
	}

	def arithmetic_eval(self, s):
		node = ast.parse(s, mode='eval')

		def _eval(node):
			if isinstance(node, ast.Expression):
				return _eval(node.body)
			elif isinstance(node, ast.Str):
				return node.s
			elif isinstance(node, ast.Num):
				return node.n
			elif isinstance(node, ast.BinOp):
				return self.binOps[type(node.op)](_eval(node.left), _eval(node.right))
			elif isinstance(node, ast.Call):
				return self.callOps[node.func.id](*[_eval(arg) for arg in node.args])
			else:
				raise Exception('Unsupported type {}'.format(node))

		return _eval(node.body)

	def execute(self, bot, user, message, channel):
		try:
			args = message.split()
			expression = tuple(args[1::])
		except IndexError:
			bot.send_message(channel, "Usage example: _math 1 + 1")
		else:
			try:
				pool = multiprocessing.pool.Pool(processes=1)
				async_result = pool.apply_async(self.arithmetic_eval, args=expression)

				result = async_result.get(timeout=self.COOLDOWN)

				bot.send_message(channel, str(result))
			except TimeoutError:
				bot.send_message(channel, f"Timed out after {self.COOLDOWN} seconds.")
			except Exception as e:
				bot.send_message(channel, str(e.__class__.__name__) + ": " + str(e))
