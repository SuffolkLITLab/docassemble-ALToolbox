import unittest

import locale
from decimal import Decimal
from .al_income import (
    ALIncome,
    ALIncomeList,
    ALAsset,
    ALAssetList,
    ALVehicle,
    ALVehicleList,
    ALSimpleValue,
    ALSimpleValueList,
    ALItemizedJob,
    ALItemizedJobList,
    ALItemizedValueDict,
    ALItemizedValue,
    recent_years,
)


class test_correct_outputs(unittest.TestCase):
    def test_simple_value(self):
        value = ALSimpleValue(transaction_type="expense", value=5)
        self.assertEqual(Decimal(-5), value.total())
        value.transaction_type = "asset"
        self.assertEqual(Decimal(5), value.total())

        value_str = ALSimpleValue(value="5.3")
        self.assertEqual(Decimal("5.3"), value_str.total())
        value_neg_str = ALSimpleValue(transaction_type="expense", value="5.3")
        self.assertEqual(Decimal("-5.3"), value_neg_str.total())
        value_float = ALSimpleValue(value=6.3)
        self.assertEqual(Decimal("6.3"), value_float.total())
        self.assertEqual("6.30", str(value_float.total()))

    def test_simple_value_list(self):
        val1 = ALSimpleValue(transaction_type="expense", source="real estate", value=5)
        val2 = ALSimpleValue(transaction_type="asset", source="job", value=10.1)
        val_list = ALSimpleValueList(elements=[val1, val2])
        self.assertEqual(Decimal("5.1"), val_list.total())
        self.assertSetEqual(set(["real estate", "job"]), val_list.sources())
        val_list.elements.append(
            ALSimpleValue(transaction_type="asset", source="job", value=20.1)
        )
        self.assertSetEqual(set(["real estate", "job"]), val_list.sources())

    def test_income(self):
        income = ALIncome(value=10.1, times_per_year=12)
        self.assertEqual(Decimal("121.2"), income.total())
        self.assertEqual(Decimal("10.1"), income.total(times_per_year=12))
        self.assertEqual(
            Decimal("2.33"), income.total(times_per_year=52).quantize(Decimal("0.01"))
        )

        hourly_income = ALIncome(
            value=4.4, times_per_year=52, is_hourly=True, hours_per_period=39
        )
        self.assertEqual(Decimal("8923.2"), hourly_income.total())
        self.assertEqual(Decimal("171.6"), hourly_income.total(52))

    def test_income_list(self):
        income = ALIncome(source="coding", value=12.53, times_per_year=12)
        hourly_income = ALIncome(
            source="coding",
            value=4.4,
            times_per_year=2,
            is_hourly=True,
            hours_per_period=41,
        )
        income_list = ALIncomeList(elements=[income, hourly_income])
        self.assertSetEqual(set(["coding"]), income_list.sources())

        self.assertEqual(Decimal(0), income_list.total(0))
        self.assertEqual(Decimal("511.16"), income_list.total(1))
        self.assertEqual(Decimal("511.16"), income_list.total(1, source="coding"))
        self.assertEqual(Decimal(0), income_list.total(1, source="wrong job"))
        self.assertEqual(
            Decimal("511.16"), income_list.total(1, source=["coding", "wrong job"])
        )

    def test_job(self):
        # TODO
        pass

    def test_job_list(self):
        # TODO
        pass

    def test_asset(self):
        home = ALAsset(market_value=1234567.89, source="home")
        self.assertEqual(Decimal(0), home.total())
        savings = ALAsset(
            balance=12.34, value=0.12, times_per_year=12, source="savings account"
        )
        self.assertEqual(Decimal("1.44"), savings.total())

    def test_asset_list(self):
        home = ALAsset(market_value=1234567.89, source="home")
        savings = ALAsset(
            balance=12.34, value=0.12, times_per_year=12, source="savings"
        )
        investing = ALAsset(
            balance=23.45, value=1.2, times_per_year=12, source="stocks"
        )
        checking = ALAsset(
            balance=34.56, value=0.01, times_per_year=12, source="checking"
        )
        asset_list = ALAssetList(elements=[home, savings, investing, checking])
        self.assertEqual(Decimal("1234567.89"), asset_list.market_value(source="home"))
        self.assertEqual(
            Decimal("35.79"), asset_list.balance(source=["savings", "stocks"])
        )
        self.assertEqual(
            Decimal("15.84"), asset_list.total(exclude_source=["checking"])
        )

    def test_asset_list_with_arabic(self):
        # arabic locales have 3 frac_digits
        existing_locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, "ar_AE.UTF-8")
        home = ALAsset(market_value=1234567.89, source="home")
        savings = ALAsset(
            balance=12.34, value=0.12, times_per_year=12, source="savings"
        )
        investing = ALAsset(
            balance=23.45, value=1.2, times_per_year=12, source="stocks"
        )
        checking = ALAsset(
            balance=34.56, value=0.01, times_per_year=12, source="checking"
        )
        asset_list = ALAssetList(elements=[home, savings, investing, checking])
        self.assertEqual(Decimal("1234567.890"), asset_list.market_value(source="home"))
        self.assertEqual(
            Decimal("35.790"), asset_list.balance(source=["savings", "stocks"])
        )
        self.assertEqual(
            Decimal("15.840"), asset_list.total(exclude_source=["checking"])
        )
        locale.setlocale(locale.LC_ALL, existing_locale)

    def test_vehicle(self):
        # TODO
        pass

    def test_vehicle_list(self):
        # TODO
        pass

    def test_itemized_value_dict(self):
        itemized_dict = ALItemizedValueDict(
            elements={
                "val1": ALItemizedValue(
                    value=5.30, exists=True, is_hourly=False, times_per_year=1
                ),
                "val2": ALItemizedValue(
                    value=5.30, exists=False, is_hourly=False, times_per_year=1
                ),
            }
        )
        itemized_dict.hook_after_gather()
        self.assertEqual(1, len(itemized_dict))

    def test_itemized_job(self):
        job = ALItemizedJob(
            is_hourly=True,
            is_part_time=True,
            name="Baby sitter",
            source="job",
            times_per_year=52,
        )
        job.to_add["part time"] = ALItemizedValue(is_hourly=True, value=10.04)
        job.hours_per_period = 10
        self.assertEqual(Decimal("5220.80"), job.gross_total())
        job.to_add["tips"] = ALItemizedValue(is_hourly=False, value=200.23)
        job.to_subtract["snacks"] = ALItemizedValue(is_hourly=False, value="24.21")
        self.assertEqual(Decimal("15632.76"), job.gross_total())
        self.assertEqual("15632.76", str(job.gross_total()))
        self.assertEqual(Decimal("1258.92"), job.deduction_total())
        self.assertEqual(Decimal("104.91"), job.deduction_total(times_per_year=12))
        self.assertEqual(Decimal("14373.84"), job.net_total())
        self.assertEqual("14373.84", str(job.net_total()))

    def test_itemized_job_list(self):
        job = ALItemizedJob(
            is_hourly=True,
            is_part_time=True,
            name="Baby sitter",
            source="job",
            times_per_year=52,
            hours_per_period=10,
        )
        job.to_add["part time"] = ALItemizedValue(is_hourly=True, value=10.04)
        job.to_add["tips"] = ALItemizedValue(is_hourly=False, value=200.23)
        job.to_subtract["snacks"] = ALItemizedValue(is_hourly=False, value="24.21")
        job_list = ALItemizedJobList(elements=[job])
        self.assertEqual(Decimal("15632.76"), job_list.gross_total())
        self.assertEqual(Decimal("1258.92"), job_list.deduction_total())
        self.assertEqual(Decimal("104.91"), job_list.deduction_total(times_per_year=12))
        self.assertEqual(Decimal("14373.84"), job_list.net_total())


if __name__ == "__main__":
    # By default we test with US locale.
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    unittest.main()
