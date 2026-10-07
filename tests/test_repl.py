from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from app.exceptions import OperationError, ValidationError
from app.calculator_repl import calculator_repl  


def test_calculator_repl_help(monkeypatch, capsys):
    """Test the 'help' command output and immediate exit."""
    inputs = iter(["help", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "Calculator started. Type 'help' for commands." in captured
    assert "Available commands:" in captured
    assert "add, subtract, multiply, divide, power, root" in captured
    assert "Goodbye!" in captured


def test_calculator_repl_exit_with_save_exception(monkeypatch, capsys):
    """Test exiting REPL when save_history raises an exception."""
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch("app.calculator.Calculator.save_history", side_effect=Exception("Disk full")):
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Warning: Could not save history: Disk full" in captured
    assert "Goodbye!" in captured


def test_calculator_repl_history_empty_and_populated(monkeypatch, capsys):
    """Test 'history' command when history is empty and after adding a calculation."""
    inputs = iter([
        "history",  # Check empty
        "add", "5", "3",  # Perform calculation
        "history",  # Check populated
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "No calculations in history" in captured
    assert "Result: 8" in captured
    assert "Calculation History:" in captured
    assert "1. 5 + 3 = 8" in captured or "1." in captured  # Matches history print format


def test_calculator_repl_clear_undo_redo(monkeypatch, capsys):
    """Test 'undo', 'redo', and 'clear' command paths."""
    inputs = iter([
        "undo",  # Nothing to undo initially
        "add", "10", "2",
        "undo",  # Undone
        "redo",  # Redone
        "clear",  # Cleared
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "Nothing to undo" in captured
    assert "Operation undone" in captured
    assert "Operation redone" in captured
    assert "History cleared" in captured


def test_calculator_repl_save_and_load(monkeypatch, capsys):
    """Test 'save' and 'load' commands and their exception handling."""
    inputs = iter([
        "save",
        "load",
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "History saved successfully" in captured
    assert "History loaded successfully" in captured


def test_calculator_repl_save_and_load_exceptions(monkeypatch, capsys):
    """Test failure outputs when save or load fail."""
    inputs = iter(["save", "load", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch("app.calculator.Calculator.save_history", side_effect=Exception("Save failed")), \
         patch("app.calculator.Calculator.load_history", side_effect=Exception("Load failed")):
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Error saving history: Save failed" in captured
    assert "Error loading history: Load failed" in captured


def test_calculator_repl_arithmetic_cancel(monkeypatch, capsys):
    """Test cancelling an operation on first and second operand prompt."""
    inputs = iter([
        "add", "cancel",  # Cancel on operand 1
        "multiply", "5", "cancel",  # Cancel on operand 2
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert captured.count("Operation cancelled") == 2


def test_calculator_repl_operation_errors(monkeypatch, capsys):
    """Test handling of ValidationError and OperationError (e.g., divide by zero or invalid input)."""
    inputs = iter([
        "divide", "10", "0",  # Trigger divide by zero
        "add", "invalid_num", "5",  # Trigger validation error
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "Error:" in captured


def test_calculator_repl_unknown_command(monkeypatch, capsys):
    """Test entering an unrecognized command."""
    inputs = iter(["foobar", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr().out
    assert "Unknown command: 'foobar'." in captured


def test_calculator_repl_keyboard_interrupt_and_eof(monkeypatch, capsys):
    """Test handling of KeyboardInterrupt (Ctrl+C) and EOFError (Ctrl+D)."""
    # First call raises KeyboardInterrupt, second raises EOFError to break out
    
    inputs = iter([KeyboardInterrupt(), EOFError()])
    exception = iter([KeyboardInterrupt(), EOFError()])

    def mock_input(_):
        val = next(inputs)
        if isinstance(val, BaseException):
            raise val
        return val

    monkeypatch.setattr("builtins.input", mock_input)

    calculator_repl()

    captured = capsys.readouterr().out
    assert "Operation cancelled" in captured
    assert "Input terminated. Exiting..." in captured


def test_calculator_repl_fatal_initialization_error(capsys):
    """Test fatal exception during REPL setup."""
    with patch("app.calculator.Calculator.__init__", side_effect=Exception("Initialization failed")):
        with pytest.raises(Exception, match="Initialization failed"):
            calculator_repl()

    captured = capsys.readouterr().out
    assert "Fatal error: Initialization failed" in captured

def test_calculator_repl_validation_and_operation_errors(monkeypatch, capsys):
    """Covers lines 138-140: handling of ValidationError and OperationError."""
    inputs = iter([
        "add", "10", "2",
        "divide", "10", "0",
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    # Mock perform_operation to raise ValidationError on first call, OperationError on second
    with patch("app.calculator.Calculator.perform_operation") as mock_op:
        mock_op.side_effect = [
            ValidationError("Invalid input format"),
            OperationError("Cannot divide by zero")
        ]
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Error: Invalid input format" in captured
    assert "Error: Cannot divide by zero" in captured

def test_calculator_repl_generic_loop_exception(monkeypatch, capsys):
    """Covers lines 154-157: generic Exception handling inside the while loop."""
    inputs = iter([
        "history",
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    # Trigger a generic Exception during command processing
    with patch("app.calculator.Calculator.show_history", side_effect=Exception("Database connection lost")):
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Error: Database connection lost" in captured

def test_calculator_repl_validation_error_coverage(monkeypatch, capsys):
    """Hits lines 138-140 via ValidationError."""
    inputs = iter([
        "add", "10", "2",
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch("app.calculator.Calculator.perform_operation", side_effect=ValidationError("Invalid operand")):
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Error: Invalid operand" in captured


def test_calculator_repl_operation_error_coverage(monkeypatch, capsys):
    """Hits lines 138-140 via OperationError."""
    inputs = iter([
        "divide", "10", "0",
        "exit"
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch("app.calculator.Calculator.perform_operation", side_effect=OperationError("Division by zero")):
        calculator_repl()

    captured = capsys.readouterr().out
    assert "Error: Division by zero" in captured