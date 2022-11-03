import unittest
from .business_days import (
    is_business_day,
    get_next_business_day,
    get_date_after_n_business_days,
)
from docassemble.base.util import today, as_datetime


class TestBusinessDays(unittest.TestCase):
    def test_is_business_day(self):
        self.assertFalse(is_business_day("2022-09-05"))
        self.assertTrue(is_business_day("2022-09-06"))
        this_years_christmas = today().replace(month=12, day=25)
        self.assertFalse(is_business_day(this_years_christmas))

    def test_get_date_after_n_business_days(self):
        self.assertEquals(
            get_date_after_n_business_days("2022-12-24", 5), as_datetime("2023-01-03")
        )


if __name__ == "__main__":
    unittest.main()
