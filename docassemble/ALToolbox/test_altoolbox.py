import unittest
from .business_days import is_business_day, get_next_business_day
from docassemble.base.util import today


class TestBusinessDays(unittest.TestCase):
    def test_is_business_day(self):
        self.assertFalse(is_business_day("2022-0-05"))
        self.assertTrue(is_business_day("2022-09-06"))
        this_years_christmas = today().replace(month=12, day=25)
        self.assertFalse(is_business_day(this_years_christmas))
