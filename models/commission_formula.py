
import ast
import math
import operator


VARIABLES = {
    "sale_price": "Цена продажи",
    "manufacturer_price": "Цена производителя",
    "purchase_price": "Закупочная стоимость товара",
    "purchase_shipping": "Доставка при закупке",
    "packaging": "Расходы на упаковку",
    "buyer_shipping": "Доставка покупателю",
}

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


class FormulaError(ValueError):
    pass


def evaluate_formula(expression, values):
    """Безопасно вычисляет разрешённое математическое выражение."""

    if not expression or len(expression) > 500:
        raise FormulaError("Формула пустая или слишком длинная.")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate_node(tree.body, values)
    except FormulaError:
        raise
    except (SyntaxError, ArithmeticError, TypeError, ValueError) as error:
        raise FormulaError(
            "Не удалось вычислить формулу. Проверьте выражение и исходные данные."
        ) from error

    if not math.isfinite(result):
        raise FormulaError("Результат формулы не является конечным числом.")

    return result


def _evaluate_node(node, values):
    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float):
            raise FormulaError("В формуле разрешены только числа.")

        return node.value

    if isinstance(node, ast.Name):
        if node.id not in VARIABLES:
            raise FormulaError(f"Неизвестная переменная: {node.id}")

        if node.id not in values or values[node.id] is None:
            raise FormulaError(
                f"Не хватает данных: {VARIABLES[node.id]}."
            )

        value = values[node.id]

        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise FormulaError(
                f"Некорректное значение: {VARIABLES[node.id]}."
            )

        return value

    if isinstance(node, ast.BinOp):
        operation = OPERATORS.get(type(node.op))

        if operation is None:
            raise FormulaError("Этот математический оператор не разрешён.")

        left = _evaluate_node(node.left, values)
        right = _evaluate_node(node.right, values)

        result = operation(left, right)

        if not math.isfinite(result):
            raise FormulaError("Результат вычисления слишком велик.")

        return result

    if isinstance(node, ast.UnaryOp) and isinstance(
        node.op, (ast.UAdd, ast.USub)
    ):
        value = _evaluate_node(node.operand, values)
        return value if isinstance(node.op, ast.UAdd) else -value

    raise FormulaError("Формула содержит недопустимую конструкцию.")
