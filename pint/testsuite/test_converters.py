import itertools
from decimal import Decimal

import pytest

from pint import UnitRegistry
from pint.compat import np
from pint.converters import Converter
from pint.facets.nonmultiplicative.definitions import (
    LogarithmicConverter,
    OffsetConverter,
)
from pint.facets.plain import ScaleConverter
from pint.testsuite import helpers


class TestConverter:
    def test_converter(self):
        c = Converter()
        assert c.is_multiplicative
        assert not c.is_logarithmic
        assert c.to_reference(8)
        assert c.from_reference(8)

    def test_multiplicative_converter(self):
        c = ScaleConverter(20.0)
        assert c.is_multiplicative
        assert not c.is_logarithmic
        assert c.from_reference(c.to_reference(100)) == 100
        assert c.to_reference(c.from_reference(100)) == 100

    def test_offset_converter(self):
        c = OffsetConverter(20.0, 2)
        assert not c.is_multiplicative
        assert not c.is_logarithmic
        assert c.from_reference(c.to_reference(100)) == 100
        assert c.to_reference(c.from_reference(100)) == 100

    def test_log_converter(self):
        c = LogarithmicConverter(scale=1, logbase=10, logfactor=1)
        assert not c.is_multiplicative
        assert c.is_logarithmic
        assert round(abs(c.to_reference(0) - 1), 7) == 0
        assert round(abs(c.to_reference(1) - 10), 7) == 0
        assert round(abs(c.to_reference(2) - 100), 7) == 0
        assert round(abs(c.from_reference(1) - 0), 7) == 0
        assert round(abs(c.from_reference(10) - 1), 7) == 0
        assert round(abs(c.from_reference(100) - 2), 7) == 0
        arb_value = 20.0
        assert (
            round(abs(c.from_reference(c.to_reference(arb_value)) - arb_value), 7) == 0
        )
        assert (
            round(abs(c.to_reference(c.from_reference(arb_value)) - arb_value), 7) == 0
        )

    @helpers.requires_numpy
    def test_converter_inplace(self):
        for c in (ScaleConverter(20.0), OffsetConverter(20.0, 2)):
            fun1 = lambda x, y: c.from_reference(c.to_reference(x, y), y)
            fun2 = lambda x, y: c.to_reference(c.from_reference(x, y), y)
            for fun, (inplace, comp) in itertools.product(
                (fun1, fun2), ((True, True), (False, False))
            ):
                a = np.ones((1, 10))
                ac = np.ones((1, 10))
                r = fun(a, inplace)
                np.testing.assert_allclose(r, ac)
                if comp:
                    assert a is r
                else:
                    assert a is not r

    @helpers.requires_numpy
    def test_log_converter_inplace(self):
        arb_value = 3.14
        c = LogarithmicConverter(scale=1, logbase=10, logfactor=1)

        from_to = lambda value, inplace: c.from_reference(
            c.to_reference(value, inplace), inplace
        )

        to_from = lambda value, inplace: c.to_reference(
            c.from_reference(value, inplace), inplace
        )

        for fun, (inplace, comp) in itertools.product(
            (from_to, to_from), ((True, True), (False, False))
        ):
            arb_array = arb_value * np.ones((1, 10))
            result = fun(arb_array, inplace)
            np.testing.assert_allclose(result, arb_array)
            if comp:
                assert arb_array is result
            else:
                assert arb_array is not result

    def test_from_arguments(self):
        assert Converter.from_arguments(scale=1) == ScaleConverter(1)
        assert Converter.from_arguments(scale=2, offset=3) == OffsetConverter(2, 3)
        assert Converter.from_arguments(
            scale=4, logbase=5, logfactor=6
        ) == LogarithmicConverter(4, 5, 6)


def count_trailing_zeros(value):

    value_string = str(value)

    if len(value_string.split(".")) == 1:
        return 0

    else:
        right_of_decimal_point = value_string.split(".")[1]
        return len(right_of_decimal_point) - len(right_of_decimal_point.rstrip("0"))


@pytest.mark.parametrize(
    "value,trailing_zeros",
    [
        (Decimal("10"), 0),
        (Decimal("10.0"), 1),
        (Decimal("10.00"), 2),
        (Decimal("10.002"), 0),
    ],
)
def test_count_trailing_zeros(value, trailing_zeros):

    assert count_trailing_zeros(value) == trailing_zeros


@pytest.fixture
def decimal_registry():
    """returns a registry that uses Decimal for non-int"""
    return UnitRegistry(non_int_type=Decimal)


@pytest.mark.parametrize("expression", [("2 microliter milligram/liter")])
def test_significance_after_conversion(decimal_registry, expression):

    value = decimal_registry.parse_expression(expression)

    value_trailing_zeros = count_trailing_zeros(value.m)
    value_compact_trailing_zeros = count_trailing_zeros(value.to_compact())
    value_converted_trailing_zeros = count_trailing_zeros(value.to("ng").m)

    assert (
        value_trailing_zeros
        == value_compact_trailing_zeros
        == value_converted_trailing_zeros
    )
