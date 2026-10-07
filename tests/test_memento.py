import datetime
from decimal import Decimal
from app.calculation import Calculation
from app.calculator_memento import CalculatorMemento


def test_calculator_memento_repr():
    fixed_time = datetime.datetime(2026, 10, 6, 20, 0, 0)
    calc1 = Calculation(operation="Addition", operand1=Decimal("5"), operand2=Decimal("2"))
    calc2 = Calculation(operation="Subtraction", operand1=Decimal("10"), operand2=Decimal("3"))

    memento = CalculatorMemento(history=[calc1, calc2], timestamp=fixed_time)

    # Use !r inside the f-string to let Python auto-format each object's exact repr
    expected_repr = f"CalculatorMemento(history=[{calc1!r}, {calc2!r}], timestamp={fixed_time!r})"

    assert repr(memento) == expected_repr

def test_calculator_memento_to_dict():
    fixed_time = datetime.datetime(2026, 10, 6, 20, 0, 0)
    calc1 = Calculation(operation="Addition", operand1=Decimal("5"), operand2=Decimal("2"))
    calc2 = Calculation(operation="Subtraction", operand1=Decimal("10"), operand2=Decimal("3"))

    memento = CalculatorMemento(history=[calc1, calc2], timestamp=fixed_time)
    
    expected_dict = {
        'history': [calc1.to_dict(), calc2.to_dict()],
        'timestamp': '2026-10-06T20:00:00'
    }

    assert memento.to_dict() == expected_dict


def test_calculator_memento_from_dict():
    data = {
        'history': [
            {'operation': 'Addition', 'operand1': Decimal("5"), 'operand2': Decimal("2"), 'result': Decimal("7"), 'timestamp': '2026-10-06T20:00:00'},
            {'operation': 'Subtraction', 'operand1': Decimal("10"), 'operand2': Decimal("3"), 'result': Decimal("7"), 'timestamp': '2026-10-06T20:00:00'}
        ],
        'timestamp': '2026-10-06T20:00:00'
    }

    memento = CalculatorMemento.from_dict(data)

    assert len(memento.history) == 2
    assert memento.timestamp == datetime.datetime(2026, 10, 6, 20, 0, 0)
    assert isinstance(memento.history[0], Calculation)
