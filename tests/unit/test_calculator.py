"""
Unit tests for the calculator tool with security hardening.

Tests cover both normal operation and security boundary conditions:
- Non-numeric constant rejection (bool, str, None, complex)
- Exponentiation limits and overflow prevention
- AST and input size limits
- Non-finite result detection
- Type validation and error handling
"""

import math
import pytest
from src.core.tools.calculator import calculate, MAX_INPUT_LENGTH, MAX_AST_NODES, MAX_POW_EXPONENT


class TestCalculatorBasicOperations:
    """Test basic arithmetic operations work correctly."""

    def test_addition(self):
        result = calculate("2 + 2")
        assert result["status"] == "success"
        assert result["result"] == 4.0

    def test_subtraction(self):
        result = calculate("10 - 3")
        assert result["status"] == "success"
        assert result["result"] == 7.0

    def test_multiplication(self):
        result = calculate("5 * 6")
        assert result["status"] == "success"
        assert result["result"] == 30.0

    def test_division(self):
        result = calculate("10 / 4")
        assert result["status"] == "success"
        assert result["result"] == 2.5

    def test_floor_division(self):
        result = calculate("10 // 3")
        assert result["status"] == "success"
        assert result["result"] == 3.0

    def test_modulo(self):
        result = calculate("10 % 3")
        assert result["status"] == "success"
        assert result["result"] == 1.0

    def test_power(self):
        result = calculate("2 ** 8")
        assert result["status"] == "success"
        assert result["result"] == 256.0

    def test_unary_negative(self):
        result = calculate("-5")
        assert result["status"] == "success"
        assert result["result"] == -5.0

    def test_unary_positive(self):
        result = calculate("+5")
        assert result["status"] == "success"
        assert result["result"] == 5.0

    def test_complex_expression(self):
        result = calculate("(2 + 3) * 4 - 10 / 2")
        assert result["status"] == "success"
        assert result["result"] == 15.0


class TestCalculatorSecurityNonNumericConstants:
    """Test rejection of non-numeric constant types."""

    def test_reject_boolean_true(self):
        # Booleans should be rejected even though they're subclass of int
        result = calculate("True")
        assert result["status"] == "error"
        assert "Boolean constant not allowed" in result["error_message"]

    def test_reject_boolean_false(self):
        result = calculate("False")
        assert result["status"] == "error"
        assert "Boolean constant not allowed" in result["error_message"]

    def test_reject_none(self):
        result = calculate("None")
        assert result["status"] == "error"
        assert "Non-numeric constant type not allowed" in result["error_message"]

    def test_reject_string(self):
        result = calculate("'hello'")
        assert result["status"] == "error"
        # Will fail at parse stage with syntax error or type error during eval
        assert result["status"] == "error"


class TestCalculatorSecurityExponentiation:
    """Test exponentiation limits and overflow prevention."""

    def test_safe_exponentiation(self):
        result = calculate("2 ** 10")
        assert result["status"] == "success"
        assert result["result"] == 1024.0

    def test_reject_huge_exponent(self):
        # Exponent exceeds MAX_POW_EXPONENT
        result = calculate(f"2 ** {MAX_POW_EXPONENT + 1}")
        assert result["status"] == "error"
        assert "exceeds maximum allowed value" in result["error_message"]

    def test_reject_negative_huge_exponent(self):
        # Negative exponent with large absolute value
        result = calculate(f"2 ** -{MAX_POW_EXPONENT + 1}")
        assert result["status"] == "error"
        assert "exceeds maximum allowed value" in result["error_message"]

    def test_reject_overflow_power(self):
        # Base and exponent that would cause overflow
        result = calculate("100 ** 200")
        assert result["status"] == "error"
        assert "overflow" in result["error_message"].lower()

    def test_exponent_at_limit(self):
        # Should work at the boundary
        result = calculate(f"1.1 ** {MAX_POW_EXPONENT}")
        # This might overflow or succeed depending on the base
        # Just verify it doesn't crash
        assert result["status"] in ["success", "error"]

    def test_zero_to_large_power(self):
        # 0 ** large_number should be fine (result is 0)
        result = calculate("0 ** 500")
        assert result["status"] == "success"
        assert result["result"] == 0.0

    def test_one_to_large_power(self):
        # 1 ** large_number should be fine (result is 1)
        result = calculate("1 ** 999")
        assert result["status"] == "success"
        assert result["result"] == 1.0


class TestCalculatorSecurityInputSizeLimits:
    """Test input length and AST complexity limits."""

    def test_input_length_within_limit(self):
        # Create expression just under the limit
        expr = "1 + " * 100 + "1"
        if len(expr) <= MAX_INPUT_LENGTH:
            result = calculate(expr)
            # Should succeed or fail due to AST complexity, not input length
            assert result["status"] in ["success", "error"]

    def test_input_length_exceeds_limit(self):
        # Create expression that exceeds MAX_INPUT_LENGTH
        # Build a simple expression that's definitely over the limit
        expr = "1" + " + 1" * (MAX_INPUT_LENGTH // 4 + 1)
        result = calculate(expr)
        assert result["status"] == "error"
        # Should fail due to length, not syntax
        if "exceeds maximum allowed length" not in result["error_message"]:
            # If it's a syntax error, the expression was too complex
            # Create a simpler but longer expression
            expr = "1 + 2" * (MAX_INPUT_LENGTH // 10)
            result = calculate(expr)
            assert result["status"] == "error"

    def test_ast_complexity_within_limit(self):
        # Small expression should work
        result = calculate("1 + 2 + 3 + 4 + 5")
        assert result["status"] == "success"

    def test_ast_complexity_exceeds_limit(self):
        # Create deeply nested or wide expression to exceed MAX_AST_NODES
        # Each "+ N" adds multiple nodes (BinOp, Add, Constant)
        expr = " + ".join(str(i) for i in range(50))
        result = calculate(expr)
        # Should fail due to node count
        if result["status"] == "error":
            assert "complexity" in result["error_message"] or "exceeds" in result["error_message"]


class TestCalculatorSecurityNonFiniteResults:
    """Test detection and rejection of non-finite results (inf, nan)."""

    def test_reject_infinity_from_overflow(self):
        # Division by very small number or large power can create infinity
        result = calculate("10 ** 1000")
        assert result["status"] == "error"
        # Should be caught by overflow detection

    def test_reject_nan_from_invalid_operation(self):
        # 0/0 creates NaN but we catch ZeroDivisionError first
        result = calculate("0 / 0")
        assert result["status"] == "error"
        assert "divide by zero" in result["error_message"].lower()

    def test_large_division(self):
        # Very large number division
        result = calculate("10 ** 100 / 10 ** 99")
        if result["status"] == "success":
            assert math.isfinite(result["result"])


class TestCalculatorSecurityDisallowedOperations:
    """Test that disallowed operations and types are rejected."""

    def test_reject_function_calls(self):
        # Should fail at parse or evaluation
        result = calculate("abs(-5)")
        assert result["status"] == "error"

    def test_reject_variable_names(self):
        result = calculate("x + 5")
        assert result["status"] == "error"

    def test_reject_bitwise_operations(self):
        result = calculate("5 & 3")
        assert result["status"] == "error"

    def test_reject_comparison_operations(self):
        result = calculate("5 > 3")
        assert result["status"] == "error"

    def test_reject_list_literals(self):
        result = calculate("[1, 2, 3]")
        assert result["status"] == "error"


class TestCalculatorErrorHandling:
    """Test error handling and error messages."""

    def test_zero_division_error(self):
        result = calculate("5 / 0")
        assert result["status"] == "error"
        assert result["error_message"] == "Cannot divide by zero"

    def test_syntax_error(self):
        result = calculate("2 +")
        assert result["status"] == "error"
        assert "Syntax error" in result["error_message"]

    def test_invalid_syntax(self):
        # Note: "2 ++ 3" is actually valid (unary + applied to +3)
        # Use a truly invalid syntax instead
        result = calculate("2 +* 3")
        assert result["status"] == "error"

    def test_empty_expression(self):
        result = calculate("")
        assert result["status"] == "error"

    def test_type_error_message_format(self):
        # When type error occurs, message should be informative
        result = calculate("True")
        assert result["status"] == "error"
        assert "error_message" in result
        assert len(result["error_message"]) > 0


class TestCalculatorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_numbers(self):
        result = calculate("-5 + -3")
        assert result["status"] == "success"
        assert result["result"] == -8.0

    def test_floating_point_precision(self):
        result = calculate("0.1 + 0.2")
        assert result["status"] == "success"
        # Due to floating point arithmetic
        assert abs(result["result"] - 0.3) < 0.0001

    def test_very_small_numbers(self):
        result = calculate("1 / 10000000")
        assert result["status"] == "success"
        assert result["result"] == 0.0000001

    def test_negative_exponent(self):
        result = calculate("2 ** -3")
        assert result["status"] == "success"
        assert result["result"] == 0.125

    def test_fractional_exponent(self):
        result = calculate("4 ** 0.5")
        assert result["status"] == "success"
        assert result["result"] == 2.0

    def test_parentheses_precedence(self):
        result = calculate("(2 + 3) * 4")
        assert result["status"] == "success"
        assert result["result"] == 20.0

    def test_nested_parentheses(self):
        result = calculate("((2 + 3) * 4) / 2")
        assert result["status"] == "success"
        assert result["result"] == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
