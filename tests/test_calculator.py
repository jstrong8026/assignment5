import datetime
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import MagicMock, Mock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from typing import cast
from app.calculator import Calculator
from app.calculator_repl import calculator_repl
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import Operation, OperationFactory

# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = CalculatorConfig(base_dir=temp_path)

        # Patch properties to use the temporary directory paths
        with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
             patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
             patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
             patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
            
            # Set return values to use paths within the temporary directory
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

@patch('app.calculator.pd.read_csv')
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history(mock_exists, mock_read_csv, calculator):
    # Mock CSV data to match the expected format in from_dict
    mock_read_csv.return_value = pd.DataFrame({
        'operation': ['Addition'],
        'operand1': ['2'],
        'operand2': ['3'],
        'result': ['5'],
        'timestamp': [datetime.datetime.now().isoformat()]
    })
    
    # Test the load_history functionality
    try:
        calculator.load_history()
        # Verify history length after loading
        assert len(calculator.history) == 1
        # Verify the loaded values
        assert calculator.history[0].operation == "Addition"
        assert calculator.history[0].operand1 == Decimal("2")
        assert calculator.history[0].operand2 == Decimal("3")
        assert calculator.history[0].result == Decimal("5")
    except OperationError:
        pytest.fail("Loading history failed due to OperationError")
        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test REPL Commands (using patches for input/output handling)

@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        calculator_repl()
        mock_save_history.assert_called_once()
        mock_print.assert_any_call("History saved successfully.")
        mock_print.assert_any_call("Goodbye!")

# Test failed to save history on exit
@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_failed_save_history(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        mock_save_history.side_effect = Exception("Disk full")
        calculator_repl()
        mock_save_history.assert_called_once()
        mock_print.assert_any_call("Warning: Could not save history: Disk full")
        mock_print.assert_any_call("Goodbye!")


#Test No calculations in history

@patch('builtins.input', side_effect=['history', 'exit'])
@patch('builtins.print')
def test_calculator_repl_history_empty(mock_print, mock_input):
    with patch('app.calculator.Calculator.show_history', return_value=[]):
        calculator_repl()
        mock_print.assert_any_call("No calculations in history")

@patch('builtins.input', side_effect=['history', 'exit'])
@patch('builtins.print')
def test_calculator_repl_history_with_entries(mock_print, mock_input):
    with patch('app.calculator.Calculator.show_history', return_value=["1 + 1 = 2", "5 * 2 = 10"]):
        calculator_repl()
        mock_print.assert_any_call("\nCalculation History:")
        mock_print.assert_any_call("1. 1 + 1 = 2")
        mock_print.assert_any_call("2. 5 * 2 = 10")

@patch('builtins.input', side_effect=['clear', 'exit'])
@patch('builtins.print')
def test_calculator_repl_clear_history(mock_print, mock_input):
     with patch('app.calculator_repl.Calculator') as MockCalculator:
        mock_calc = MockCalculator.return_value
        calculator_repl()
        mock_calc.clear_history.assert_called_once()
        mock_print.assert_any_call("History cleared")

#Test history undo / redo commands

@patch('builtins.input', side_effect=['undo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_undo_success(mock_print, mock_input):
    with patch('app.calculator.Calculator.undo', return_value=True):
        calculator_repl()
        mock_print.assert_any_call("Operation undone")

@patch('builtins.input', side_effect=['undo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_undo_failure(mock_print, mock_input):
    with patch('app.calculator.Calculator.undo', return_value=False):
        calculator_repl()
        mock_print.assert_any_call("Nothing to undo")

@patch('builtins.input', side_effect=['redo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_redo_success(mock_print, mock_input):
    with patch('app.calculator.Calculator.redo', return_value=True):
        calculator_repl()
        mock_print.assert_any_call("Operation redone")

@patch('builtins.input', side_effect=['redo', 'exit'])
@patch('builtins.print')
def test_calculator_repl_redo_failure(mock_print, mock_input):
    with patch('app.calculator.Calculator.redo', return_value=False):
        calculator_repl()
        mock_print.assert_any_call("Nothing to redo")

@patch('builtins.input', side_effect=['save', 'exit'])
@patch('builtins.print')
def test_calculator_repl_save_history_failure(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history', side_effect=Exception("Disk error")):
        calculator_repl()
        mock_print.assert_any_call("Error saving history: Disk error")


@patch('builtins.input', side_effect=['load', 'exit'])
@patch('builtins.print')
def test_calculator_repl_load_history_failure(mock_print, mock_input):
    with patch('app.calculator.Calculator.load_history', side_effect=Exception("File not found")):
        calculator_repl()
        mock_print.assert_any_call("Error loading history: File not found")

@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
def test_calculator_repl_help(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nAvailable commands:")

@patch('builtins.input', side_effect=['add', '2', '3', 'exit'])
@patch('builtins.print')
def test_calculator_repl_addition(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nResult: 5")


@patch('builtins.input', side_effect=['add', 'cancel', 'exit'])
@patch('builtins.print')
def test_calculator_repl_arithmetic_cancel_first_number(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Operation cancelled")


# Test cancelling operation at second prompt
@patch('builtins.input', side_effect=['multiply', '10', 'CANCEL', 'exit'])
@patch('builtins.print')
def test_calculator_repl_arithmetic_cancel_second_number(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("Operation cancelled")

class SimpleOperation(Operation):
    """Pure Python concrete operation to avoid MagicMock __str__ issues."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        return a + b

    def __str__(self) -> str:
        return "Addition"


# 1. Cover Lines 103-106: Setup logging exception handling
def test_setup_logging_exception(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator.__new__(Calculator)
    calc.config = config

    with patch('builtins.print') as mock_print:
        with patch('os.makedirs', side_effect=RuntimeError("Logging dir failure")):
            with pytest.raises(RuntimeError, match="Logging dir failure"):
                calc._setup_logging()
            mock_print.assert_any_call("Error setting up logging: Logging dir failure")


# 2. Cover Line 219: History max size truncation
def test_perform_operation_max_history_size(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path, max_history_size=2)
    calc = Calculator(config=config)
    calc.clear_history()  # Start with an explicit clean history
    calc.set_operation(SimpleOperation())

    calc.perform_operation("1", "1")
    calc.perform_operation("2", "2")
    calc.perform_operation("3", "3")  # Triggers line 219 (self.history.pop(0))

    assert len(calc.history) == 2


# 3. Cover Lines 230-233: Catch-all OperationError in perform_operation
def test_perform_operation_generic_exception(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator(config=config)

    mock_op = MagicMock()
    mock_op.execute.side_effect = RuntimeError("Unexpected math exception")
    calc.set_operation(mock_op)

    with pytest.raises(OperationError, match="Operation failed: Unexpected math exception"):
        calc.perform_operation("5", "5")


# 4. Cover Lines 272-275: Save history failure
def test_save_history_exception(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator(config=config)

    # Patch Path.mkdir at the class level so PosixPath read-only attribute errors are avoided
    with patch('pathlib.Path.mkdir', side_effect=RuntimeError("IO Disk error")):
        with pytest.raises(OperationError, match="Failed to save history: IO Disk error"):
            calc.save_history()


# 5. Cover Lines 309-312: Load history failure
def test_load_history_exception(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator(config=config)

    # Patch Path.exists and read_csv at class/module level
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pandas.read_csv', side_effect=RuntimeError("Corrupted CSV structure")):
            with pytest.raises(OperationError, match="Failed to load history: Corrupted CSV structure"):
                calc.load_history()


# 6. Cover Lines 324-333: get_history_dataframe method
def test_get_history_dataframe(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator(config=config)
    calc.clear_history()  # Ensure clean slate
    calc.set_operation(SimpleOperation())

    calc.perform_operation("5", "3")

    mock_df = MagicMock()
    mock_df.__len__.return_value = 1

    with patch('pandas.DataFrame', return_value=mock_df) as mock_df_ctor:
        df = calc.get_history_dataframe()
        assert df is mock_df
        assert mock_df_ctor.called
        passed_data = mock_df_ctor.call_args[0][0]
        assert len(passed_data) == 1
        assert passed_data[0]['operation'] == 'Addition'
        assert str(passed_data[0]['operand1']) == '5'
        assert str(passed_data[0]['operand2']) == '3'


# 7. Cover Line 390: Successful redo return True
def test_redo_success(tmp_path):
    config = CalculatorConfig(base_dir=tmp_path)
    calc = Calculator(config=config)
    calc.clear_history()  # Ensure clean slate
    calc.set_operation(SimpleOperation())

    calc.perform_operation("5", "5")
    calc.undo()

    result = calc.redo()  # Reaches return True at line 390
    assert result is True
    assert len(calc.history) == 1