"""Безпечний обчислювач математичних формул.

Замінює небезпечний eval() на парсинг AST (Abstract Syntax Tree).
Підтримує арифметичні операції, математичні функції та змінні.
"""

import ast
import math
import operator
import warnings

# Пригнічуємо DeprecationWarning для ast.Num у Python ≥3.8
warnings.filterwarnings("ignore", category=DeprecationWarning, module=__name__)


class SafeFormulaEvaluator:
    """Безпечний обчислювач математичних формул без eval().

    Підтримує:
      • Арифметика: +, -, *, /, //, %, **
      • Унарні: +, -
      • Порівняння: ==, !=, <, >, <=, >=
      • Функції: abs, round, min, max, pow, float, int
      • Модуль math: math.pi, math.e, math.sin, math.cos, math.sqrt, ...
      • Константи: pi, e, True, False
      • Змінні з namespace

    Заборонено:
      • Виклики методів об'єктів (obj.method())
      • Індексація ([])
      • Lambda, if-else вирази, list/dict/set
      • Імпорти, присвоєння
      • Доступ до __builtins__, __import__
    """

    # Дозволені бінарні оператори
    _BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    # Дозволені унарні оператори
    _UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    # Дозволені функції (ім'я → callable)
    _ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "float": float,
        "int": int,
    }

    # Дозволені імена-константи
    _ALLOWED_NAMES = {
        "pi": math.pi,
        "e": math.e,
        "True": True,
        "False": False,
        "None": None,
    }

    def __init__(self, extra_names: dict | None = None):
        self.extra_names = extra_names or {}

    def eval(self, formula: str, variables: dict | None = None) -> float:
        """Обчислити формулу безпечно.

        Args:
            formula: Рядок з математичним виразом.
            variables: Словник змінних (ім'я → значення).

        Returns:
            Результат обчислення (float, int або bool).

        Raises:
            ValueError: Якщо формула містить заборонені конструкції
                        або синтаксичну помилку.
            ZeroDivisionError: При діленні на нуль.
        """
        if not formula or not isinstance(formula, str):
            raise ValueError("Формула має бути непорожнім рядком")

        variables = variables or {}

        # Парсимо AST у режимі 'eval' (дозволяє лише вирази, не statements)
        try:
            tree = ast.parse(formula.strip(), mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Синтаксична помилка у формулі: {exc}") from exc

        return self._eval_node(tree.body, variables)

    def _eval_node(self, node: ast.AST, variables: dict):
        """Рекурсивно обчислює вузол AST."""

        # ── Числа ──
        if isinstance(node, ast.Constant):          # Python ≥3.8
            if isinstance(node.value, (int, float, complex)):
                return node.value
            if isinstance(node.value, str):
                raise ValueError("Рядкові літерали у формулі не дозволені")
            raise ValueError(f"Константа типу {type(node.value).__name__} не дозволена")

        # ── Бінарні операції (+, -, *, /, //, %, **) ──
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op_type = type(node.op)
            if op_type not in self._BIN_OPS:
                raise ValueError(f"Оператор '{op_type.__name__}' не дозволений у формулі")
            return self._BIN_OPS[op_type](left, right)

        # ── Унарні операції (+, -) ──
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, variables)
            op_type = type(node.op)
            if op_type not in self._UNARY_OPS:
                raise ValueError(f"Унарний оператор '{op_type.__name__}' не дозволений")
            return self._UNARY_OPS[op_type](operand)

        # ── Змінні (імена) ──
        if isinstance(node, ast.Name):
            name = node.id
            if name in variables:
                return variables[name]
            if name in self._ALLOWED_NAMES:
                return self._ALLOWED_NAMES[name]
            if name in self.extra_names:
                return self.extra_names[name]
            raise ValueError(f"Невідома змінна у формулі: '{name}'")

        # ── Виклики функцій ──
        if isinstance(node, ast.Call):
            # Дозволяємо лише прості виклики: func(arg1, arg2)
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self._ALLOWED_FUNCTIONS:
                    raise ValueError(f"Функція '{func_name}' не дозволена у формулі")
                args = [self._eval_node(arg, variables) for arg in node.args]
                kwargs = {
                    kw.arg: self._eval_node(kw.value, variables)
                    for kw in node.keywords
                }
                return self._ALLOWED_FUNCTIONS[func_name](*args, **kwargs)

            # Дозволяємо math.func(arg)
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    math_func_name = node.func.attr
                    if hasattr(math, math_func_name):
                        math_func = getattr(math, math_func_name)
                        args = [self._eval_node(arg, variables) for arg in node.args]
                        return math_func(*args)
                    raise ValueError(f"math.{math_func_name} не існує")
                raise ValueError("Доступ до атрибутів дозволений лише для модуля 'math'")

            raise ValueError("Складні виклики функцій не дозволені")

        # ── Атрибути (math.pi тощо) ──
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "math":
                if hasattr(math, node.attr):
                    return getattr(math, node.attr)
                raise ValueError(f"math.{node.attr} не існує")
            raise ValueError("Доступ до атрибутів дозволений лише для 'math'")

        # ── Порівняння (==, !=, <, >, <=, >=) ──
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, variables)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, variables)
                if isinstance(op, ast.Eq):
                    result = result and (left == right)
                elif isinstance(op, ast.NotEq):
                    result = result and (left != right)
                elif isinstance(op, ast.Lt):
                    result = result and (left < right)
                elif isinstance(op, ast.LtE):
                    result = result and (left <= right)
                elif isinstance(op, ast.Gt):
                    result = result and (left > right)
                elif isinstance(op, ast.GtE):
                    result = result and (left >= right)
                else:
                    raise ValueError(f"Оператор порівняння '{type(op).__name__}' не дозволений")
                left = right
            return result

        # ── Умовні вирази (a if b else c) — заборонено для безпеки ──
        if isinstance(node, ast.IfExp):
            raise ValueError("Умовні вирази (if-else) у формулах не дозволені")

        # ── Все інше — заборонено ──
        raise ValueError(
            f"Конструкція '{type(node).__name__}' не дозволена у формулі. "
            f"Дозволено: числа, змінні, арифметика, math.*, abs, round, min, max, pow"
        )


def safe_eval(formula: str, variables: dict | None = None) -> float:
    """Швидка функція для безпечного обчислення формули."""
    evaluator = SafeFormulaEvaluator()
    return evaluator.eval(formula, variables)
