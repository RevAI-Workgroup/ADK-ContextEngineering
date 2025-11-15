"""
Calculator tool for basic arithmetic operations.

This tool provides safe mathematical calculations using a restricted
evaluation environment to prevent code injection attacks.
"""

import ast
import math
import operator
from typing import Any, Dict, Union
import time

from src.core.tracing import trace_function


# Security limits for safe evaluation
MAX_INPUT_LENGTH = 1000  # Maximum length of input expression
MAX_AST_NODES = 100  # Maximum number of AST nodes to prevent DoS
MAX_POW_EXPONENT = 1000  # Maximum absolute value for exponents

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


def _count_ast_nodes(node: ast.AST) -> int:
    """
    Count the total number of nodes in an AST.

    Args:
        node: Root AST node to count from

    Returns:
        Total number of nodes in the tree
    """
    count = 1
    for child in ast.walk(node):
        if child is not node:
            count += 1
    return count


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """
    Evaluate an AST expression composed only of allowed numeric operations and return its numeric result.
    
    Accepts AST nodes representing numeric constants, binary operations, and unary operations restricted to the operators in ALLOWED_OPERATORS. Enforces safety checks including: rejection of non-numeric and boolean constants, rejection of non-finite floats, bounding of exponent values for power operations, detection of obvious power overflow, and validation that intermediate and final results are finite.
    
    Parameters:
        node (ast.AST): AST node to evaluate; must be an expression tree made of allowed node types.
    
    Returns:
        int | float: The numeric result of evaluating the AST.
    
    Raises:
        TypeError: If a constant is not an int/float or if a boolean constant is provided.
        ValueError: If the node type or operator is not allowed, if numeric values are non-finite, if an exponent exceeds MAX_POW_EXPONENT, or if an operation would produce an overflow or otherwise invalid result.
    """
    if isinstance(node, ast.Constant):
        value = node.value
        # Validate constant is only int or float (reject bool, None, str, complex, etc.)
        if not isinstance(value, (int, float)):
            raise TypeError(f"Non-numeric constant type not allowed: {type(value).__name__}")
        # Note: bool is a subclass of int in Python, so we need explicit check
        if isinstance(value, bool):
            raise TypeError("Boolean constant not allowed")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite numeric constant not allowed")
        return value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not allowed")

        left = _safe_eval(node.left)
        right = _safe_eval(node.right)

        # Special handling for power operations to prevent overflow
        if isinstance(node.op, ast.Pow):
            # Check exponent bounds
            if abs(right) > MAX_POW_EXPONENT:
                raise ValueError(f"Exponent {right} exceeds maximum allowed value {MAX_POW_EXPONENT}")

            # Check for obvious overflow conditions
            if abs(left) > 1 and abs(right) > 100:
                # Estimate if result would overflow: log(|result|) ≈ |exponent| * log(|base|)
                try:
                    if abs(right) * math.log(abs(left)) > 700:  # ~log(sys.float_info.max)
                        raise ValueError("Power operation would cause overflow")
                except (ValueError, OverflowError):
                    raise ValueError("Power operation would cause overflow")

        result = ALLOWED_OPERATORS[op_type](left, right)

        # Validate result is finite
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Operation produced non-finite result (inf or nan)")

        return result
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} not allowed")
        operand = _safe_eval(node.operand)
        result = ALLOWED_OPERATORS[op_type](operand)

        # Validate result is finite
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Operation produced non-finite result (inf or nan)")

        return result
    else:
        raise ValueError(f"Expression type {type(node).__name__} not allowed")


@trace_function(attributes={"tool": "calculate"})
def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluate a limited arithmetic expression in a restricted, safe environment.
    
    Supports the operators: +, -, *, /, //, %, and **. The function enforces input length
    and AST node-count limits and validates numeric results to prevent abuse or
    unsafe results.
    
    Parameters:
        expression (str): Mathematical expression to evaluate, e.g. "2 + 2" or "3**4".
    
    Returns:
        dict: A result object with one of the following shapes:
            - Success: {"status": "success", "expression": <input>, "result": <float>}
            - Error:   {"status": "error", "expression": <input>, "error_message": <string>}
    """
    try:
        # Validate input length to prevent DoS
        if len(expression) > MAX_INPUT_LENGTH:
            raise ValueError(
                f"Expression length {len(expression)} exceeds maximum allowed length {MAX_INPUT_LENGTH}"
            )

        # Parse the expression into an AST
        tree = ast.parse(expression, mode='eval')

        # Validate AST node count to prevent DoS
        node_count = _count_ast_nodes(tree)
        if node_count > MAX_AST_NODES:
            raise ValueError(
                f"Expression complexity ({node_count} nodes) exceeds maximum allowed ({MAX_AST_NODES} nodes)"
            )

        # Safely evaluate the AST
        result = _safe_eval(tree.body)

        # Final validation that result is finite
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Calculation produced non-finite result")

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
    except (ValueError, TypeError) as e:
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
    except (OverflowError, ArithmeticError) as e:
        return {
            "status": "error",
            "expression": expression,
            "error_message": f"Arithmetic error: {str(e)}",
        }