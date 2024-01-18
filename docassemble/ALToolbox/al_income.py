# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import (
    DAObject,
    DADict,
    DAList,
    DAOrderedDict,
    DAEmpty,
    Individual,
    comma_list,
    get_locale,
    word,
    log,
    object_name_convert,
    value,
)
from decimal import Decimal
import re
import datetime
import docassemble.base.functions
import json
from typing import Any, Dict, Callable, List, Optional, Set, Union, Tuple, Mapping

__all__ = [
    "times_per_year",
    "recent_years",
    "ALIncome",
    "ALIncomeList",
    "ALExpense",
    "ALExpenseList",
    "ALJob",
    "ALJobList",
    "ALAsset",
    "ALAssetList",
    "ALVehicle",
    "ALVehicleList",
    "ALSimpleValue",
    "ALSimpleValueList",
    "ALItemizedValue",
    "ALItemizedValueDict",
    "ALItemizedJob",
    "ALItemizedJobList",
]


def _currency_float_to_decimal(value: Union[str, float]) -> Decimal:
    """Given a float (that was set by a docassemble currency datatype, so
    rounded to the nearest `fractional_digit` decimal places), returns the
    exact decimal value, without floating point representation errors
    """
    if isinstance(value, float):
        # Print out the value of the float, rounded to the smallest allowable amount in the
        # locale currency, and use this value to make the exact Decimal value
        digits = get_locale("frac_digits")
        return Decimal(f"{value:.{digits}f}")
    else:
        return Decimal(value)


def times_per_year(
    times_per_year_list: List[Tuple[int, str]], times_per_year: float
) -> str:
    """
    Get the lower-case textual description that matches a time period contained
    in a "times per year" list.

    The goal of this function is to allow you to reflect the user's selection
    back to them, either on screen or in a document.

    In `al_income.yml` there is a default `times_per_year_list`, but the list
    that you use must be passed as a parameter as it's common to want to
    customize this for a given financial statement.

    For example: if the `times_per_year` is 12, it will return "monthly" from
    the default `times_per_year_list`.

    If the times per year does not exist in the given list, it will return a
    literal string like "five times per year".

    Fractional or floating point-based times_per_year are permissible in the
    times_per_year_list, although they are not commonly used. E.g., `.5` would
    represent "every two years". Items not contained in the list (to provide a
    specific lookup name) will have a string representation that is rounded to
    the nearest whole integer.
    """
    try:
        for row in times_per_year_list:
            if float(times_per_year) == float(row[0]):
                return row[1].lower()
        return (
            docassemble.base.functions.nice_number(int(times_per_year), capitalize=True)
            + " "
            + docassemble.base.functions.word("times per year")
        )
    except:
        return str(times_per_year)


def recent_years(
    past: int = 25, order: str = "descending", future: int = 1
) -> List[int]:
    """
    Returns a list of the most recent past years, continuing into the future.
    Defaults to most recent 15 years+1. Useful to populate a combobox of years
    where the most recent ones are most likely. E.g. automobile years or
    birthdate.

    Keyword parameters:
    * past {float} The number of past years to list, including the current year.
        The default is 15
    * order {string} 'descending' or 'ascending'. Default is `descending`.
    * future (defaults to 1).
    """
    now = datetime.datetime.now()
    if order == "ascending":
        return list(range(now.year - past, now.year + future, 1))
    else:
        return list(range(now.year + future, now.year - past, -1))


class ALPeriodicAmount(DAObject):
    """
    Represents an amount (could be an income or an expense depending on the context)
    that reoccurs some times per year. E.g, to express a weekly period, use 52. The default
    is 1 (a year).

    Attributes:
    .value {str | float | Decimal} A number representing an amount of money accumulated during
        the `times_per_year` of this income.
    .times_per_year {float | Decimal} Represents a number of the annual frequency of
        the income. E.g. 12 for a monthly income.
    .source {str} (Optional) The "source" of the income, like a "job" or a "house".
    .display_name {str} (Optional) If present, will have a translated string to show the
        user, as opposed to a raw english string from the program
    """

    def __str__(self) -> str:
        """Returns the income's `.total()` as string, not its object name."""
        return str(self.total())

    def total(self, times_per_year: float = 1) -> Decimal:
        """
        Returns the income over the specified times_per_year,

        To calculate `.total()`, an ALPeriodicAmount must have a `.times_per_year` and `.value`.
        """
        val = _currency_float_to_decimal(self.value)
        return (val * Decimal(self.times_per_year)) / Decimal(times_per_year)


class ALIncome(ALPeriodicAmount):
    """
    Represents an income which may have an hourly rate or a salary. Hourly rate
    incomes must include hours per period (times per year). Period is some
    denominator of a year. E.g, to express a weekly period, use 52. The default
    is 1 (a year).

    Attributes:
    .value {str | float | Decimal} A number representing an amount of money accumulated during
        the `times_per_year` of this income.
    .times_per_year {float | Decimal} Represents a number of the annual frequency of
        the income. E.g. 12 for a monthly income.
    .is_hourly {bool} (Optional) True if the income is hourly.
    .hours_per_period {float | Decimal} (Optional) If the income is hourly, the number of
        hours during the annual frequency of this job. E.g. if the annual
        frequency is 52 (weekly), the hours per week might be 50. That is, 50
        hours per week. This attribute is required if `.is_hourly` is True.
    .source {str} (Optional) The "source" of the income, like a "job" or a "house".
    .owner {str} (Optional) Full name of the income's owner as a single string.
    """

    def total(self, times_per_year: float = 1) -> Decimal:
        """
        Returns the income over the specified times_per_year, taking into account
        hours per period for hourly items. For example, for an hourly income of 10
        an hour, 40 hours a week, `income.total(1)` would be 20,800, the yearly income,
        and `income.total(52)` would be 400, the weekly income.

        To calculate `.total()`, an ALIncome must have a `.times_per_year` and `.value`.
        It can also have `.is_hourly` and `.hours_per_period`.
        """
        if hasattr(self, "is_hourly") and self.is_hourly:
            val = _currency_float_to_decimal(self.value)
            return (
                val * Decimal(self.hours_per_period) * Decimal(self.times_per_year)
            ) / Decimal(times_per_year)
        else:
            return super().total(times_per_year=times_per_year)


class ALExpense(ALPeriodicAmount):
    """Not much changes from ALPeriodic Amount, just the generic object questions"""

    pass


SourceType = Union[Set[str], List[str], str]


def _to_set(s: Optional[Union[Set, List, str]]) -> Set:
    """Converts a str, list of strings, or set of strings into a set of strings,
    which can be used to filter items in ALIncome classes.

    This is for internal use meant to ensure that `source` input is always a set.
    """
    if s is None:
        return set()
    if isinstance(s, set):
        return s
    if isinstance(s, list):
        return set(s)
    if isinstance(s, str):
        return set([s])
    return set()


def _source_to_callable(
    source: Optional[SourceType] = None, exclude_source: Optional[SourceType] = None
) -> Callable[[str], bool]:
    """Combines both a positive and negative lists into a single set that should be tested for inclusion"""
    exclude_set = _to_set(exclude_source)
    include_set = _to_set(source).difference(exclude_set)
    if include_set:
        return lambda s: s in include_set
    else:
        if exclude_set:
            return lambda s: s not in exclude_set
        else:
            return lambda s: True


class ALIncomeList(DAList):
    """
    Represents a filterable DAList of incomes-type items. It can make
    use of these attributes and methods in its items:

    .source
    .owner
    .times_per_year
    .value
    .total()
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, "object_type") or self.object_type is None:
            self.object_type = ALIncome

    def sources(self) -> Set[str]:
        """Returns a set of the unique sources in the ALIncomeList."""
        sources = set()
        for item in self.elements:
            if hasattr(item, "source"):
                sources.add(item.source)
        return sources

    def matches(
        self, source: SourceType, exclude_source: Optional[SourceType] = None
    ) -> "ALIncomeList":
        """
        Returns an ALIncomeList consisting only of elements matching the specified
        income source, assisting in filling PDFs with predefined spaces. `source`
        may be a list.
        """
        # Always make sure we're working with a set
        satifies_sources = _source_to_callable(source, exclude_source)
        # Construct the filtered list
        return ALIncomeList(
            elements=[item for item in self.elements if satifies_sources(item.source)],
            object_type=self.object_type,
        )

    def total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
        owner: Optional[str] = None,
    ) -> Decimal:
        """
        Returns the total periodic value in the list, gathering the list items
        if necessary. You can optionally filter by `source`. `source` can be a
        string or a list. You can also filter by one `owner`.

        To calculate `.total()` correctly, all items must have a `.total()` and
        it should be a positive value. Job-type incomes should automatically
        exclude deductions.
        """
        self._trigger_gather()
        result: Decimal = Decimal(0)
        if times_per_year == 0:
            return result
        satisfies_sources = _source_to_callable(source, exclude_source)
        for item in self.elements:
            if (source is None and exclude_source is None) or (
                hasattr(item, "source") and satisfies_sources(item.source)
            ):
                if owner is None:  # if the user doesn't care who the owner is
                    result += Decimal(item.total(times_per_year=times_per_year))
                else:
                    if (
                        not (isinstance(owner, DAEmpty))
                        and hasattr(item, "owner")
                        and item.owner == owner
                    ):
                        result += Decimal(item.total(times_per_year=times_per_year))
        return result

    def move_checks_to_list(
        self,
        selected_types: Optional[DADict] = None,
        selected_terms: Optional[Mapping] = None,
    ):
        """Gives a 'gather by checklist' option.
        If no selected_types param is passed, requires that a .selected_types
        attribute be set by a `datatype: checkboxes` fields
        If "other" is in the selected_types, the source will not be set directly

        Sets the attribute "moved" to true, doesn't set gathered, because this isn't
        idempotent, so trying to also gather all info about the checks in the list doesn't
        work well.
        """
        if selected_types is None:
            selected_types = self.selected_types
        if not selected_terms:
            selected_terms = {}
        self.elements.clear()
        for source in selected_types.true_values(insertion_order=True):
            if source == "other":
                self.appendObject()
            else:
                self.appendObject(
                    source=source, display_name=selected_terms.get(source, source)
                )
        self.moved = True


class ALJob(ALIncome):
    """
    Represents a single job that may be hourly or pay-period based.

    The job can have a net and gross income figure, but it does not represent
    individual items like wages, tips or deductions that may appear on a paycheck--the
    user must enter the total amount for "net" and "gross" income for a given period.

    Can be stored in an ALJobList.

    Attributes:
    .value {float | Decimal} A number representing an amount of money accumulated during
        the `times_per_year` of this income.
    .times_per_year {float} Represents a number of the annual frequency of
        the value. E.g. 12 for a monthly value.
    .is_hourly {bool} (Optional): Whether the gross total should be calculated based on hours
        worked per week
    .hours_per_period {float} (Optional) The number of hours during the annual
        frequency of this job. E.g. if the annual frequency is 52 (weekly), the
        hours per week might be 50. That is, 50 hours per week.
    .deduction {float} (Optional) The amount of money deducted from the total value each period.
        If this job is hourly, deduction is still from each period, not each hour. Used to
        calculate the net income in `net_income()`.
    .employer {Individual} (Optional) A docassemble Individual object, employer.address is the address
        and employer.phone is the phone
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        # if not hasattr(self, "source") or self.source is None:
        #    self.source = "job"
        if not hasattr(self, "employer"):
            if hasattr(self, "employer_type"):
                self.initializeAttribute("employer", self.employer_type)
            else:
                self.initializeAttribute("employer", Individual)

    def gross_total(self, times_per_year: float = 1) -> Decimal:
        """
        Same as ALIncome total. Returns the income over the specified times_per_year,
        representing the `.value` attribute of the item.

        `times_per_year` is some denominator of a year. E.g. to express a weekly
        period, use 52. The default is 1 (a year).
        """
        return self.total(times_per_year=times_per_year)

    def deductions(self, times_per_year: float = 1) -> Decimal:
        """
        Returns the total deductions from someone's pay over the specificed times_per_year
        (not per hour if hourly).

        `times_per_year` is some denominator of a year. E.g. to express a weekly
        period, use 52. The default is 1 (a year).
        """
        deduction = _currency_float_to_decimal(self.deduction)
        return (deduction * Decimal(self.times_per_year)) / Decimal(times_per_year)

    def net_total(self, times_per_year: float = 1) -> Decimal:
        """
        Returns the net income over a time period, found using
        `self.value` and `self.deduction`.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        `self.deduction` is the amount deducted from one's pay over a period (not
        per hour if hourly).

        This will force the gathering of the ALJob's `.value` and `.deduction` attributes.
        """
        return self.total(times_per_year=times_per_year) - self.deductions(
            times_per_year=times_per_year
        )

    def employer_name_address_phone(self) -> str:
        """
        Returns name, address and phone number of employer as a string. Forces
        gathering the `.employer`, `.employer_address`, and `.employer_phone`
        attributes.
        """
        if self.employer.address.address and self.employer.phone:
            return (
                f"{self.employer.name}: {self.employer.address}, {self.employer.phone}"
            )
        if self.employer.address.address:
            return f"{self.employer.name}: {self.employer.address}"
        if self.employer.phone:
            return f"{self.employer.name}: {self.employer.phone}"
        return f"{self.employer.name}"

    def normalized_hours(self, times_per_year: float = 1) -> float:
        """
        Returns the normalized number of hours worked in a given times_per_year,
        based on the self.hours_per_period and self.times_per_year attributes.

        For example, if the person works 10 hours a week, it will return
        520 when the times_per_year parameter is 1.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        This will force the gathering of the attributes `.hours_per_period` and
        `.times_per_year`
        """
        return (float(self.hours_per_period) * int(self.times_per_year)) / float(
            times_per_year
        )


class ALJobList(ALIncomeList):
    """
    Represents a list of ALJobs. Adds the `.gross_total()` and
    `.net_total()` methods to the ALIncomeList class. It's a more common
    way of reporting income than ALItemizedJobList.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALJob

    def total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
        owner: Optional[str] = None,
    ) -> Decimal:
        """
        Returns the sum of the gross incomes of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. `source` can be a
        string or a list.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).
        """
        return self.gross_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        )

    def gross_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of the gross incomes of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. `source` can be a
        string or a list.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).
        """
        self._trigger_gather()
        result: Decimal = Decimal(0)
        if times_per_year == 0:
            return result
        satisfies_sources = _source_to_callable(source, exclude_source)
        for job in self.elements:
            if satisfies_sources(job.source):
                result += Decimal(job.gross_total(times_per_year=times_per_year))
        return result

    def net_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of the net incomes of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. `source` can be a
        string or a list. Leaving out `source` will use all sources.

        If the job is hourly, the `net_total()` may not be comparable to the
        `gross_total()`.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).
        """
        self._trigger_gather()
        result: Decimal = Decimal(0)
        if times_per_year == 0:
            return result
        satisfies_sources = _source_to_callable(source, exclude_source)
        for job in self.elements:
            if satisfies_sources(job.source):
                result += Decimal(job.net_total(times_per_year=times_per_year))
        return result

    def deductions(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of the deductions of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. Leaving out `source`
        will use all sources.
        """
        self._trigger_gather()
        result: Decimal = Decimal(0)
        if times_per_year == 0:
            return result
        satisfies_sources = _source_to_callable(source, exclude_source)
        for job in self.elements:
            if satisfies_sources(job.source):
                result += Decimal(job.deductions(times_per_year=times_per_year))
        return result


class ALExpenseList(ALIncomeList):
    """
    A list of expenses

    * each element has a:
        * value
        * source
        * display name
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALExpense


class ALAsset(ALIncome):
    """
    An ALAsset represents an asset that has a market value, an optional income
    that the asset earns, and an optional balance which may be helpful if the
    asset represents a financial account rather than a physical asset.

    Can be stored in an ALAssetList.

    Attributes:
     .market_value {float | Decimal} Market value of the asset.
    .balance {float | Decimal } Current balance of the account, e.g., like
        the balance in a checking account, but could also represent a loan
        amount.
    .value {float | Decimal} (Optional) Represents the income the asset earns
        for a given `times_per_year`, such as interest earned in a checking
        account. If not defined, the income will be set to 0, to simplify
        representing the many common assets that do not earn any income.
    .times_per_year {float} (Optional) Number of times per year the asset
        earns the income listed in the `value` attribute.
    .owner {str} (Optional) Full name of the asset owner as a single string.
    .source {str} (Optional) The "source" of the asset, like "vase".
    """

    def total(self, times_per_year: float = 1) -> Decimal:
        """
        Returns the .value attribute divided by the times per year you want to calculate. The value defaults to 0.

        `times_per_year` is some denominator of a year. E.g, to express a weekly period, use 52. The default is 1 (a year).

        Args:
            times_per_year (float, optional): The number of times per year to calculate. Defaults to 1.

        Returns:
            Decimal: The .value attribute divided by the times per year.
        """
        if not hasattr(self, "value") or self.value == "":
            return Decimal(0)
        else:
            return super(ALAsset, self).total(times_per_year=times_per_year)

    def equity(self, loan_attribute="balance") -> Decimal:
        """
        Returns the total equity in the asset (e.g., market value minus balance).

        Args:
            loan_attribute (str, optional): The attribute of the asset to use as the loan value. Defaults to "balance".

        Returns:
            Decimal: The total equity in the asset.
        """
        if getattr(self, loan_attribute, None) is None:
            return Decimal(self.market_value)
        return Decimal(self.market_value) - Decimal(getattr(self, loan_attribute))


class ALAssetList(ALIncomeList):
    """
    A list of ALAssets. The `total()` of the list will be the total income
    earned, which may not be what you want for a list of assets. To get the
    total value of all assets, use the `market_value()` method.

    Attributes:
        market_value (float | Decimal): Market value of the asset.
        balance (float | Decimal): Current balance of the account, e.g., like
            the balance in a checking account, but could also represent a loan
            amount.
        value (float | Decimal, optional): Represents the income the asset earns
            for a given `times_per_year`, such as interest earned in a checking
            account. If not defined, the income will be set to 0, to simplify
            representing the many common assets that do not earn any income.
        times_per_year (float, optional): Number of times per year the asset
            earns the income listed in the `value` attribute.
        owner (str, optional): Full name of the asset owner as a single string.
        source (str, optional): The "source" of the asset, like "vase".
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALAsset

    def market_value(
        self,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the total `.market_value` of assets in the list.

        You can filter the assets by `source`. `source` can be a string or a list.

        Args:
            source (Optional[SourceType]): The source of the assets to include in the calculation.
                If None, all sources are included. Can be a string or a list.
            exclude_source (Optional[SourceType]): The source of the assets to exclude from the calculation.
                If None, no sources are excluded.

        Returns:
            Decimal: The total market value of the assets.
        """
        result = Decimal(0)
        satisfies_sources = _source_to_callable(source, exclude_source)
        for asset in self.elements:
            if (source is None and exclude_source is None) or (
                satisfies_sources(asset.source)
            ):
                result += _currency_float_to_decimal(asset.market_value)
        return result

    def balance(
        self,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the total `.balance` of assets in the list, which typically corresponds to the available funds in a financial account.

        You can filter the assets by `source`. `source` can be a string or a list.

        Args:
            source (Optional[SourceType]): The source of the assets to include in the calculation.
                If None, all sources are included. Can be a string or a list.
            exclude_source (Optional[SourceType]): The source of the assets to exclude from the calculation.
                If None, no sources are excluded.

        Returns:
            Decimal: The total balance of the assets.
        """
        self._trigger_gather()
        result = Decimal(0)
        satisfies_sources = _source_to_callable(source, exclude_source)
        for asset in self.elements:
            if (source is None and exclude_source is None) or (
                satisfies_sources(asset.source)
            ):
                result += _currency_float_to_decimal(asset.balance)
        return result

    def equity(
        self,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
        loan_attribute: str = "balance",
    ) -> Decimal:
        """
        Calculates and returns the total equity in the assets.

        This method triggers the gathering of assets, then iterates over each asset. If a source or exclude_source is not
        specified, or if the asset's source satisfies the source criteria, the equity of the asset is added to the total.

        Args:
            source (Optional[SourceType]): The source of the assets to include in the calculation. If None, all sources are included.
            exclude_source (Optional[SourceType]): The source of the assets to exclude from the calculation. If None, no sources are excluded.
            loan_attribute (str, optional): The attribute of the asset to use as the loan value. Defaults to "balance".

        Returns:
            Decimal: The total equity in the assets.
        """
        self._trigger_gather()
        result = Decimal(0)
        satisfies_sources = _source_to_callable(source, exclude_source)
        for asset in self.elements:
            if (source is None and exclude_source is None) or (
                satisfies_sources(asset.source)
            ):
                result += asset.equity(loan_attribute=loan_attribute)
        return result

    def owners(
        self,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Set[str]:
        """
        Returns a set of the unique owners of the assets.

        You can filter the assets by `source`. `source` can be a string or a list.

        Args:
            source (Optional[SourceType]): The source of the assets to include in the calculation.
                If None, all sources are included. Can be a string or a list.
            exclude_source (Optional[SourceType]): The source of the assets to exclude from the calculation.
                If None, no sources are excluded.

        Returns:
            Set[str]: A set of the unique owners of the assets.
        """
        owners = set()
        if source is None and exclude_source is None:
            for asset in self.elements:
                if hasattr(asset, "owner"):
                    owners.add(asset.owner)
        else:
            satisfies_source = _source_to_callable(source, exclude_source)
            for asset in self.elements:
                if (
                    hasattr(asset, "owner")
                    and hasattr(asset, "source")
                    and satisfies_source(asset.source)
                ):
                    owners.add(asset.owner)
        return owners


class ALVehicle(ALAsset):
    """Represents a vehicle as a specialized type of ALAsset.

    This subclass of ALAsset adds specific attributes relevant to vehicles,
    such as year, make, and model, and includes methods for representing
    these attributes in a standardized format, as often required on financial
    statement forms.

    Attributes:
        year (str): The model year of the vehicle, e.g., '2022'.
        make (str): The make of the vehicle, e.g., 'Honda'.
        model (str): The model of the vehicle, e.g., 'Accord'.
        market_value (float or Decimal): Market value of the vehicle.
        balance (float or Decimal): Balance of the loan on the vehicle.
        value (float or Decimal, optional): Income earned by the vehicle, typically 0.
        times_per_year (int): The frequency over which the `value` is earned annually.
        owner (str): Full name of the vehicle owner.
        source (str, optional): The source of the asset, defaults to 'vehicle'.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, "source"):
            self.source = "vehicle"

    def year_make_model(self, separator: str = " / ") -> str:
        """
        Returns a string of the format year/make/model of the vehicle. Triggers
        gathering those attributes.

        Args:
            separator {str} (Optional) The separator between the year, make and model.

        Returns:
            A string of the format year/make/model of the vehicle.
        """
        return separator.join(map(str, [self.year, self.make, self.model]))


class ALVehicleList(ALAssetList):
    """List of ALVehicles. Extends ALAssetList."""

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALVehicle


class ALSimpleValue(DAObject):
    """
    Represents a currency value. It's meant to be stored in a list. Can be an
        item in an ALSimpleValueList.

    Attributes:
    .value {str | float } The monetary value of the item.
    .transaction_type {str} (Optional) Can be "expense", which will give a
        negative value to the total of the item.
    .source {str} (Optional) The "source" of the item, like "vase".
    """

    def total(self) -> Decimal:
        """
        If desired, to use as a ledger, values can be signed (mixed positive and
        negative). Setting transaction_type = 'expense' makes the value negative.
        Use min=0 in that case.

        If you use signed values, be careful when placing in an ALIncomeList
        object. The `total()` method may return unexpected results in that case.
        """
        val = _currency_float_to_decimal(self.value)
        if hasattr(self, "transaction_type"):
            return val * Decimal(-1) if (self.transaction_type == "expense") else val
        else:
            return val

    def __str__(self) -> str:
        """Returns the total as a formatted string"""
        return str(self.total())


class ALSimpleValueList(DAList):
    """Represents a filterable DAList of ALSimpleValues."""

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALSimpleValue

    def sources(self) -> Set:
        """
        Returns a set of the unique sources of values stored in the list.
        """
        sources = set()
        for value in self.elements:
            if hasattr(value, "source"):
                sources.add(value.source)
        return sources

    def total(
        self,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the total value in the list, gathering the list items if
        necessary. You can filter the values by `source`. `source` can be a
        string or a list.
        """
        self._trigger_gather()
        result = Decimal(0)
        if source is None and exclude_source is None:
            for value in self.elements:
                result += value.total()
        else:
            satisfies_source = _source_to_callable(source, exclude_source)
            for value in self.elements:
                if satisfies_source(value.source):
                    result += value.total()
        return result


class ALItemizedValue(DAObject):
    """
    An item in an ALItemizedValueDict (a line item like wages, tips or union dues).
    Should be a positive number, even if it will later be subtracted from the
    job's net total.

    WARNING: This item's period-based value can't be calculated correctly
    outside of an ALItemizedJob. Its value should only be accessed through the
    filtering methods of the ALItemizedJob that contains it.

    Attributes:
    .value {float | Decimal} A number representing an amount of money accumulated
        during the `times_per_year` of this item or this item's job.
    .is_hourly {bool} Whether this particular item is calculated hourly.
    .times_per_year { float} A denominator of a year representing the annual
         frequency of the job. E.g. 12 for monthly.
    .exists {bool} (Optional) Allows an interview author to pre-define some common
        descriptors, like "wages" or "union dues" without requiring the user to
        provide a value for each item.

        If the ".exists" attribute is False or undefined, the item will not be used
        when calculating totals.
    """

    def income_fields(self, use_exists=True) -> List[Dict[str, Any]]:
        """
        Returns a YAML structure representing the list of fields for an itemized value,
        to be passed to a `code` attribute of a question's fields
        """
        if use_exists:
            return [
                {
                    "label": self.display_name,
                    "field": self.attr_name("exists"),
                    "datatype": "yesno",
                },
                {
                    "label": word("Amount"),
                    "field": self.attr_name("value"),
                    "show if": self.attr_name("exists"),
                    "datatype": "currency",
                    "min": 0,
                },
            ]
        else:
            return [
                {
                    "label": self.display_name,
                    "field": self.attr_name("value"),
                    "datatype": "currency",
                    "min": 0,
                },
            ]

    def total(self) -> Decimal:
        # If an item's value doesn't exist, use a value of 0
        # TODO: is this behavior correct, or should it force gathering the value?
        # What does a no-value item in the list represent?
        if not hasattr(self, "value") or hasattr(self, "exists") and not self.exists:
            return Decimal(0)

        return _currency_float_to_decimal(self.value)

    def __str__(self) -> str:
        """Returns a string of the value of the item with two decimal places."""
        currency_str = "{:.2f}".format(self.value)
        return currency_str

    def __float__(self) -> float:
        if hasattr(self, "exists") and not self.exists:
            return 0.0
        else:
            return float(self.value)

    def __int__(self) -> int:
        return int(float(self))

    def __format__(self, format_spec) -> str:
        return f"{float(self):{format_spec}}"


class ALItemizedValueDict(DAOrderedDict):
    """
    Dictionary that can contain ALItemizedValues (e.g. line items) for an
    ALItemizedJob. E.g., wages, tips and deductions being the most common.

    An ALItemizedJob will have two ALItemizedValueDicts, one for income
    and one for deductions.

    WARNING: Should only be accessed through an ALItemizedJob. Otherwise
        you may get unexpected results.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALItemizedValue
        if not hasattr(self, "complete_attribute"):
            self.complete_attribute = "value"

    def hook_after_gather(self) -> None:
        """
        Update item lists after they've been gathered or edited to remove non-existent
        items. Will still allow the developer to set `auto_gather=False` if they
        want without affecting this functionality.
        See https://docassemble.org/docs/objects.html#DAList.hook_after_gather.

        If a developer wants to remove these items _before_ gathering is finished,
        they can use similar code in their question's `validation code:`
        """
        keys_to_delete = []
        # During the loop, the list has to stay steady, so don't delete those items.
        # `.elements.items()` example of preventing gathering in `validation code:`
        for key, value in self.elements.items():
            if hasattr(value, "exists") and value.exists is False:
                keys_to_delete.append(key)
        # Delete the keys
        for key in keys_to_delete:
            self.delitem(key)

    def total(self) -> Decimal:
        val = Decimal(0)
        for key, value in self.elements.items():
            if hasattr(value, "exists") and not value.exists:
                continue
            val += _currency_float_to_decimal(value.value)
        return val

    def __str__(self) -> str:
        """
        Returns a string of the dictionary's key/value pairs as two-element lists in a list.
        E.g. '[["federal_taxes", "2500.00"], ["wages", "15.50"]]'
        """
        to_stringify = []
        for key in self:
            to_stringify.append((key, "{:.2f}".format(self[key].value)))
        pretty = json.dumps(to_stringify, indent=2)
        return pretty


class ALItemizedJob(DAObject):
    """
    An "Itemized" job is a job which allows the user to report very specific,
    granular details about the money that they earn in that job and any
    deductions that they have on their paycheck. This detailed accounting of
    money for each job is required on some financial statements, although in
    many financial statements, just reporting gross and net income is sufficient.

    For example, an ALItemizedJob can let the user report:
    - Wages at one hourly rate
    - Overtime at a second hourly rate
    - Tips earned during that time period
    - A fixed salary earned for that pay period
    - Union Dues
    - Insurance
    - Taxes

    If the financial statement only requires "gross" and "net" income, the
    ALJobList has a simpler API and may be the preferred way to represent the
    income in code.

    Attributes:
    .to_add {ALItemizedValueDict} Dict of ALItemizedValues that would be added
        to a job's net total, like wages and tips.
    .to_subtract {ALItemizedValueDict} Dict of ALItemizedValues that would be
        subtracted from a net total, like union dues or insurance premiums.
    .times_per_year {float} A denominator of a year, like 12 for monthly, that
        represents how frequently the income is earned
    .is_hourly {bool} (Optional) Whether the value represents a figure that the
        user earns on an hourly basis, rather than for the full time period
    .hours_per_period {int} (Optional) If the job is hourly, how many hours the
        user works per period.
    .employer {Individual} (Optional) Individual assumed to have a name and,
        optionally, an address and phone.
    .source {str} (Optional) The category of this item, like "public service".
        Defaults to "job".

    WARNING: Individual items in `.to_add` and `.to_subtract` should not be used
        directly. They should only be accessed through the filtering methods of
        this job.

    Fulfills these requirements:
    - A job can be hourly. Its wages will be calculated with that in mind.
    - Despite an hourly job, some individual items must be calculated using the
        job's whole period.
    - Some items will have their own periods.
    - In a list of jobs, a developer may need to access full time and part time
        jobs separately.
    - In a list of jobs, a developer may need to sum all items from one source,
        such as tips or taxes.
    - The developer needs access to total money coming in, total money going out,
        and the total of money going in and money coming out.
    - A user must be able to add their own arbitrary items.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        # if not hasattr(self, "source") or self.source is None:
        #    self.source = "job"
        if not hasattr(self, "employer"):
            if hasattr(self, "employer_type"):
                self.initializeAttribute("employer", self.employer_type)
            else:
                self.initializeAttribute("employer", Individual)
        # Money coming in
        if not hasattr(self, "to_add"):
            self.initializeAttribute("to_add", ALItemizedValueDict)
        # Money being taken out
        if not hasattr(self, "to_subtract"):
            self.initializeAttribute("to_subtract", ALItemizedValueDict)

    def _item_value_per_times_per_year(
        self, item: ALItemizedValue, times_per_year: float = 1
    ) -> Decimal:
        """
        Given an ALItemizedValue and a times_per_year, returns the value
        accumulated by the item for that `times_per_year`, applying the
        attributes of the top-level ALItemizedJob, such as `times_per_year` and
        `is_hourly` as a default, and otherwise applying the attributes of the
        ALItemizedValue.

        `times_per_year` is some denominator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        Args:
        arg item {ALItemizedValue} Object containing the value and other props
            for an "in" or "out" ALItemizedJob item.
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        """
        if times_per_year == 0:
            return Decimal(0)

        # If an item has its own period, use that
        # Otherwise, default to the parent times_per_year
        if hasattr(item, "times_per_year") and item.times_per_year:
            frequency_to_use = item.times_per_year
        else:
            frequency_to_use = self.times_per_year

        # Both the job and the item itself need to be hourly to be
        # calculated as hourly
        is_hourly = self.is_hourly and hasattr(item, "is_hourly") and item.is_hourly
        value = item.total()

        # Use the appropriate calculation
        if is_hourly:
            # NOTE: fixes a bug that was present < 0.8.2
            try:
                hours_per_period = Decimal(self.hours_per_period)
            except:
                log(
                    word(
                        "Your hours per period need to be just a single number, without words"
                    ),
                    "danger",
                )
                delattr(self, "hours_per_period")
                self.hours_per_period  # Will cause another exception

            return (
                value * Decimal(hours_per_period) * Decimal(frequency_to_use)
            ) / Decimal(times_per_year)
        else:
            return (value * Decimal(frequency_to_use)) / Decimal(times_per_year)

    def total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Alias for ALItemizedJob.gross_total to integrate with ALIncomeList math.
        """
        return self.gross_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        )

    def gross_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of positive values (payments) for a given times_per_year.
        You can filter the items by `source`. `source` can be a string or a list.
        If you use sources from deductions, they will be ignored.

        Args:
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_add._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Add up all money coming in from a source
        satisfies_sources = _source_to_callable(source, exclude_source)
        for key, value in self.to_add.elements.items():
            if satisfies_sources(key):
                total += self._item_value_per_times_per_year(
                    value, times_per_year=times_per_year
                )
        return total

    def deduction_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of money going out (normally, deductions like union
        dues) divided by a pay times_per_year as a positive value. You can
        filter the items by `source`. `source` can be a string or a list.

        Args:
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | List[str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_subtract._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list of sources (names?)
        # Add up all money coming in from a source
        satisfies_sources = _source_to_callable(source, exclude_source)
        for key, value in self.to_subtract.elements.items():
            if satisfies_sources(key):
                total += self._item_value_per_times_per_year(
                    value, times_per_year=times_per_year
                )
        return total

    def net_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the net (gross minus deductions) value of the job divided by
        `times_per_year`. You can filter the items by `source`. `source` can be a
        string or a list. E.g. "full time" or ["full time", "union dues"]

        Args:
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | List[str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_add._trigger_gather()
        # self.to_subtract._trigger_gather()
        return self.gross_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        ) - self.deduction_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        )

    def employer_name_address_phone(self) -> str:
        """
        Returns concatenation of employer name and, if they exist, employer
        address and phone number.
        """
        info_list = []
        has_address = (
            hasattr(self.employer.address, "address") and self.employer.address.address
        )
        has_number = (
            hasattr(self.employer, "phone_number") and self.employer.phone_number
        )
        # Create a list so we can take advantage of `comma_list` instead
        # of doing further fiddly list manipulation
        if has_address:
            info_list.append(self.employer.address.on_one_line())
        if has_number:
            info_list.append(self.employer.phone_number)
        # If either exist, add a colon and the appropriate strings
        if has_address or has_number:
            return (
                f"{ self.employer.name.full(middle='full') }: {comma_list( info_list )}"
            )
        return self.employer.name.full(middle="full")

    def normalized_hours(self, times_per_year: float = 1) -> float:
        """
        Returns the normalized number of hours worked in a given times_per_year,
        based on the self.hours_per_period and self.times_per_year attributes.

        For example, if the person works 10 hours a week, it will return
        520 when the times_per_year parameter is 1.
        """
        return (float(self.hours_per_period) * float(self.times_per_year)) / float(
            times_per_year
        )


class ALItemizedJobList(DAList):
    """
    Represents a list of ALItemizedJobs that can have both payments and money
        out. This is a less common way of reporting income.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, "source") or self.source is None:
            self.source = "jobs"
        if not hasattr(self, "object_type") or self.object_type is None:
            self.object_type = ALItemizedJob

    def sources(self, which_side: Optional[str] = None) -> Set[str]:
        """Returns a set of the unique sources in all of the jobs.
        By default gets from both sides, if which_side is "deductions", only gets from deductions.
        """
        sources = set()
        if not which_side:
            which_side = "all"
        for job in self.elements:
            if which_side == "all" or which_side == "incomes":
                sources.update(job.to_add.keys())
            if which_side == "all" or which_side == "deductions":
                sources.update(job.to_subtract.keys())
        return sources

    def total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Alias for ALItemizedJobList.gross_total to integrate with
        ALIncomeList math.
        """
        return self.gross_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        )

    def gross_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of the gross incomes of the list's jobs divided by the
        times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'commissions']
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Add all job gross totals from particular sources
        for job in self.elements:
            total += job.gross_total(
                times_per_year=times_per_year,
                source=source,
                exclude_source=exclude_source,
            )
        return total

    def deduction_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the sum of the deductions of the list's jobs divided by the
        times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['taxes', 'dues']
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Add all the money going out for all jobs
        for job in self.elements:
            total += job.deduction_total(
                times_per_year=times_per_year,
                source=source,
                exclude_source=exclude_source,
            )
        return total

    def net_total(
        self,
        times_per_year: float = 1,
        source: Optional[SourceType] = None,
        exclude_source: Optional[SourceType] = None,
    ) -> Decimal:
        """
        Returns the net of the list's jobs (money in minus money out) divided by
        the times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | List[str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'taxes']
        kwarg: times_per_year {float} (Optional) Number of times per year you
            want to calculate. E.g, to express a weekly period, use 52. Default is 1.
        """
        return self.gross_total(
            times_per_year=times_per_year, source=source
        ) - self.deduction_total(
            times_per_year=times_per_year, source=source, exclude_source=exclude_source
        )
