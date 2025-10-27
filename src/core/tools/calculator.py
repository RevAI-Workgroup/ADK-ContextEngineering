"""
Calculator tool for basic arithmetic operations.

This tool provides safe mathematical calculations using a restricted
evaluation environment to prevent code injection attacks.
"""

import ast
import operator
from typing import Any, Dict


# Allowed operators for safe evaluation
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    """
    Safely evaluate an AST node containing only allowed operations.

    Args:
        node: AST node to evaluate

    Returns:
        Result of the evaluation

    Raises:
        ValueError: If the expression contains disallowed operations
    """
    if isinstance(node, ast.Num):  # Python 3.7 compatibility
        return node.n
    elif isinstance(node, ast.Constant):  # Python 3.8+
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not allowed")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not allowed")
        operand = _safe_eval(node.operand)
        return ALLOWED_OPERATORS[op_type](operand)
    else:
        raise ValueError(f"Expression type {type(node).__name__} not allowed")


def calculate(expression: str) -> Dict[str, Any]:
    """
    Perform basic arithmetic calculations safely.

    Supports addition (+), subtraction (-), multiplication (*), division (/),
    floor division (//), modulo (%), and exponentiation (**).

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5", "2 ** 8")

    Returns:
        dict: Result with status and value or error message

    Examples:
        >>> calculate("2 + 2")
        {"status": "success", "expression": "2 + 2", "result": 4.0}

        >>> calculate("10 / 3")
        {"status": "success", "expression": "10 / 3", "result": 3.333...}
    """
    try:
        # Parse the expression into an AST
        tree = ast.parse(expression, mode='eval')

        # Safely evaluate the AST
        result = _safe_eval(tree.body)

        return {
            "status": "success",
            "expression": expression,
            "result": float(result),
        }

    except ZeroDivisionError:
        return {
            "status": "error",
            "expression": expression,
            "error_message": "Cannot divide by zero",
        }
    except ValueError as e:
        return {
            "status": "error",
            "expression": expression,
            "error_message": f"Invalid expression: {str(e)}",
        }
    except SyntaxError:
        return {
            "status": "error",
            "expression": expression,
            "error_message": "Syntax error in mathematical expression",
        }
    except Exception as e:
        return {
            "status": "error",
            "expression": expression,
            "error_message": f"Calculation failed: {str(e)}",
        }
