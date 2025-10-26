"""
Unit tests for cross-platform timeout functionality.
"""

import pytest
import time

from src.evaluation.evaluator import call_with_timeout, TimeoutError


class TestTimeoutFunction:
    """Test suite for call_with_timeout function."""
    
    def test_function_completes_within_timeout(self):
        """Test that fast function completes normally."""
        def fast_function(x, y):
            return x + y
        
        result = call_with_timeout(
            func=fast_function,
            args=(2, 3),
            timeout_seconds=5
        )
        
        assert result == 5
    
    def test_function_with_kwargs(self):
        """Test function with keyword arguments."""
        def func_with_kwargs(a, b=10):
            return a * b
        
        result = call_with_timeout(
            func=func_with_kwargs,
            args=(5,),
            kwargs={'b': 3},
            timeout_seconds=5
        )
        
        assert result == 15
    
    def test_function_timeout(self):
        """Test that slow function triggers timeout."""
        def slow_function():
            time.sleep(10)  # Sleep for 10 seconds
            return "completed"
        
        with pytest.raises(TimeoutError) as exc_info:
            call_with_timeout(
                func=slow_function,
                timeout_seconds=1  # Timeout after 1 second
            )
        
        assert "timed out" in str(exc_info.value).lower()
    
    def test_function_raises_exception(self):
        """Test that exceptions from function are propagated."""
        def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError) as exc_info:
            call_with_timeout(
                func=error_function,
                timeout_seconds=5
            )
        
        assert "Test error" in str(exc_info.value)
    
    def test_function_returns_none(self):
        """Test function that returns None."""
        def none_function():
            return None
        
        result = call_with_timeout(
            func=none_function,
            timeout_seconds=5
        )
        
        assert result is None
    
    def test_function_with_no_args(self):
        """Test function with no arguments."""
        def no_arg_function():
            return "success"
        
        result = call_with_timeout(
            func=no_arg_function,
            timeout_seconds=5
        )
        
        assert result == "success"
    
    def test_timeout_works_cross_platform(self):
        """Test that timeout works on current platform (Unix or Windows)."""
        import platform
        
        def sleep_function():
            time.sleep(3)
            return "should not reach here"
        
        # This should timeout regardless of platform
        with pytest.raises(TimeoutError):
            call_with_timeout(
                func=sleep_function,
                timeout_seconds=1
            )
        
        # Test passed on both Unix and Windows
        print(f"Timeout test passed on {platform.system()}")
    
    def test_exact_timeout_boundary(self):
        """Test behavior at timeout boundary."""
        def boundary_function():
            time.sleep(0.5)
            return "completed"
        
        # Should complete (0.5s < 1s timeout)
        result = call_with_timeout(
            func=boundary_function,
            timeout_seconds=1
        )
        
        assert result == "completed"
    
    def test_multiple_calls_independent(self):
        """Test that multiple calls don't interfere with each other."""
        def quick_function(value):
            return value * 2
        
        # Multiple rapid calls
        result1 = call_with_timeout(quick_function, args=(5,), timeout_seconds=5)
        result2 = call_with_timeout(quick_function, args=(10,), timeout_seconds=5)
        result3 = call_with_timeout(quick_function, args=(15,), timeout_seconds=5)
        
        assert result1 == 10
        assert result2 == 20
        assert result3 == 30

