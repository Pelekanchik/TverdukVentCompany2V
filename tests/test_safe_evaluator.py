"""Тести для SafeFormulaEvaluator.

Запуск:  pytest tests/test_safe_evaluator.py -v
"""

import math
import pytest

from ventilation_company.calculations.safe_evaluator import SafeFormulaEvaluator, safe_eval


class TestSafeFormulaEvaluator:
    """Базові тести обчислення формул."""

    def test_simple_arithmetic(self):
        e = SafeFormulaEvaluator()
        assert e.eval("2 + 2") == 4
        assert e.eval("10 - 3") == 7
        assert e.eval("4 * 5") == 20
        assert e.eval("20 / 4") == 5.0
        assert e.eval("2 ** 3") == 8
        assert e.eval("17 % 5") == 2
        assert e.eval("7 // 2") == 3

    def test_decimal_numbers(self):
        e = SafeFormulaEvaluator()
        assert abs(e.eval("3.14 * 2") - 6.28) < 0.001
        assert e.eval("0.1 + 0.2") == pytest.approx(0.3, abs=1e-9)

    def test_variables(self):
        e = SafeFormulaEvaluator()
        ns = {"metal_area": 1.5, "material_price": 580.0, "thickness": 0.7}
        result = e.eval("metal_area * material_price * 1.15", ns)
        assert result == pytest.approx(1.5 * 580.0 * 1.15)

    def test_math_functions(self):
        e = SafeFormulaEvaluator()
        assert e.eval("abs(-5)") == 5
        assert e.eval("round(3.14159, 2)") == 3.14
        assert e.eval("min(5, 3, 8)") == 3
        assert e.eval("max(5, 3, 8)") == 8
        assert e.eval("pow(2, 3)") == 8
        # sum([1,2,3]) не працює, бо списки заборонені для безпеки
        # у реальних формулах списки не використовуються

    def test_math_module(self):
        e = SafeFormulaEvaluator()
        assert e.eval("math.pi") == pytest.approx(math.pi)
        assert e.eval("math.sqrt(16)") == 4.0
        assert e.eval("math.sin(0)") == 0.0
        assert e.eval("math.cos(0)") == 1.0
        assert e.eval("math.ceil(2.3)") == 3
        assert e.eval("math.floor(2.9)") == 2

    def test_comparisons(self):
        e = SafeFormulaEvaluator()
        assert e.eval("5 > 3") is True
        assert e.eval("5 < 3") is False
        assert e.eval("5 == 5") is True
        assert e.eval("5 != 3") is True
        assert e.eval("5 >= 5") is True
        assert e.eval("5 <= 4") is False

    def test_unary_operators(self):
        e = SafeFormulaEvaluator()
        assert e.eval("-5") == -5
        assert e.eval("+5") == 5
        assert e.eval("-(3 + 2)") == -5

    def test_complex_formula_like_original(self):
        """Формула, схожа на реальну формулу відводу."""
        e = SafeFormulaEvaluator()
        ns = {
            "A": 400, "B": 200, "C": 90,
            "D": 100, "E": 100, "F": 50,
            "material_price": 580.0,
        }
        formula = "(2*(A+B)/1000) * ((D+E)/1000 + (F+B/2)*C*math.pi/180/1000) * material_price * 1.60"
        result = e.eval(formula, ns)
        # Просто перевіряємо, що обчислюється без помилок і результат > 0
        assert result > 0
        assert isinstance(result, float)

    def test_safe_eval_shortcut(self):
        assert safe_eval("2 + 2") == 4
        assert safe_eval("x * 2", {"x": 5}) == 10


class TestSecurityBlocks:
    """Тести блокування небезпечних конструкцій."""

    def test_blocks_builtins_import(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Функція '__import__' не дозволена"):
            e.eval("__import__('os')")

    def test_blocks_object_access(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Конструкція 'Subscript' не дозволена"):
            e.eval("().__class__.__bases__[0]")

    def test_blocks_indexing(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Конструкція 'Subscript' не дозволена"):
            e.eval("[1,2,3][0]")

    def test_blocks_lambda(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Конструкція 'Lambda' не дозволена"):
            e.eval("lambda x: x * 2")

    def test_blocks_if_expression(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Умовні вирази"):
            e.eval("5 if True else 3")

    def test_blocks_open_function(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Функція 'open' не дозволена"):
            e.eval("open('/etc/passwd')")

    def test_blocks_eval_function(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Функція 'eval' не дозволена"):
            e.eval("eval('1+1')")

    def test_blocks_exec_function(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Функція 'exec' не дозволена"):
            e.eval("exec('import os')")

    def test_blocks_string_literals(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Рядкові літерали"):
            e.eval("'hello'")

    def test_blocks_dict_literal(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Конструкція 'Dict' не дозволена"):
            e.eval("{'a': 1}")

    def test_blocks_list_literal(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Конструкція 'List' не дозволена"):
            e.eval("[1, 2, 3]")

    def test_blocks_attribute_on_non_math(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Доступ до атрибутів дозволений лише для 'math'"):
            e.eval("(1).__class__")

    def test_blocks_unknown_variable(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Невідома змінна"):
            e.eval("secret_backdoor")

    def test_blocks_division_by_zero_raises(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ZeroDivisionError):
            e.eval("1 / 0")


class TestErrorMessages:
    """Тести зрозумілих повідомлень про помилки."""

    def test_empty_formula(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="непорожнім рядком"):
            e.eval("")

    def test_none_formula(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="непорожнім рядком"):
            e.eval(None)

    def test_syntax_error(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="Синтаксична помилка"):
            e.eval("2 + * 3")

    def test_unknown_operator(self):
        e = SafeFormulaEvaluator()
        with pytest.raises(ValueError, match="не дозволений"):
            e.eval("5 @ 3")  # матричне множення


class TestPricingFormulas:
    """Тести реальних формул з каталогу продукції."""

    @pytest.fixture
    def standard_ns(self):
        return {
            "metal_area": 1.2,
            "metal_area_m2": 1.2,
            "thickness": 0.7,
            "material_price": 580.0,
            "weight": 5.5,
            "weight_kg": 5.5,
            "quantity": 1,
            "bolt_count": 8,
            "length": 1000,
        }

    def test_rect_duct_formula(self, standard_ns):
        e = SafeFormulaEvaluator()
        result = e.eval("metal_area * material_price * 1.15", standard_ns)
        assert result == pytest.approx(1.2 * 580.0 * 1.15)

    def test_round_duct_formula(self, standard_ns):
        e = SafeFormulaEvaluator()
        result = e.eval("metal_area * material_price * 1.20", standard_ns)
        assert result == pytest.approx(1.2 * 580.0 * 1.20)

    def test_flange_formula(self, standard_ns):
        e = SafeFormulaEvaluator()
        result = e.eval("metal_area * material_price * 1.30 + bolt_count * 2.5", standard_ns)
        assert result == pytest.approx(1.2 * 580.0 * 1.30 + 8 * 2.5)

    def test_flexible_insert_formula(self, standard_ns):
        e = SafeFormulaEvaluator()
        result = e.eval("metal_area * 35.0 + 25.0", standard_ns)
        assert result == pytest.approx(1.2 * 35.0 + 25.0)

    def test_elbow_formula(self):
        e = SafeFormulaEvaluator()
        ns = {
            "A": 400, "B": 200, "C": 90,
            "D": 100, "E": 100, "F": 50,
            "material_price": 580.0,
        }
        formula = "(2*(A+B)/1000) * ((D+E)/1000 + (F+B/2)*C*math.pi/180/1000) * material_price * 1.60"
        result = e.eval(formula, ns)
        assert result > 0

    def test_round_elbow_formula(self):
        e = SafeFormulaEvaluator()
        ns = {
            "A": 315, "C": 90,
            "D": 100, "E": 100, "F": 50,
            "material_price": 580.0,
        }
        formula = "(math.pi*A/1000) * ((D+E)/1000 + (F+A/2)*C*math.pi/180/1000) * material_price * 1.65"
        result = e.eval(formula, ns)
        assert result > 0

    def test_custom_params(self, standard_ns):
        e = SafeFormulaEvaluator(extra_names={"flange_price": 150.0, "coating_price": 25.0})
        ns = standard_ns.copy()
        result = e.eval("metal_area * material_price * 1.15 + flange_price * 2 + coating_price", ns)
        expected = 1.2 * 580.0 * 1.15 + 150.0 * 2 + 25.0
        assert result == pytest.approx(expected)
