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
        self.assertEqual(
            get_date_after_n_business_days("2022-12-24", 5), as_datetime("2023-01-03")
        )
        self.assertEqual(
            get_date_after_n_business_days("2022-12-12", 3), as_datetime("2022-12-15")
        )
        self.assertEqual(
            get_date_after_n_business_days(
                "2022-12-12",
                3,
                add_holidays={"12-13": "fake day 1", "12-14": "fake day2"},
            ),
            as_datetime("2022-12-19"),
        )
        self.assertEqual(
            get_date_after_n_business_days(
                "2022-12-24", 5, remove_holidays=["Christmas Day"]
            ),
            as_datetime("2022-12-30"),
        )


if __name__ == "__main__":
    unittest.main()
