# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import (
    DAObject,
    DAList,
    DAOrderedDict,
    PeriodicValue,
    DAEmpty,
    Individual,
    comma_list,
    log,
    object_name_convert,
    value,
)
from decimal import Decimal
import re
import datetime
import docassemble.base.functions
import json


def times_per_year(index):
    """
    Given the index of an item in the `times_per_year_list`, returns
    text describing the number of intervals of the given period in a year.
    Example: times_per_year(12) will return "monthly"
    """
    times_per_year_list = value("times_per_year_list")
    try:
        for row in times_per_year_list:
            if int(index) == int(row[0]):
                return row[1].lower()
        return (
            docassemble.base.functions.nice_number(int(index), capitalize=True)
            + " "
            + docassemble.base.functions.word("times per year")
        )
    except:
        return ""
    return ""

def recent_years(past=15, order="descending", future=1):
    """
    Returns a list of the most recent past years, continuing into the future.
    Defaults to most recent 15 years+1. Useful to populate a combobox of years
    where the most recent ones are most likely. E.g. automobile years or
    birthdate.

    Keyword paramaters:
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


class ALIncome(PeriodicValue):
    """
    Represents an income which may have an hourly rate or a salary. Hourly rate
    incomes must include hours per period. Period is some demoninator of a year.
    E.g, to express a weekly period, use 52. The default is 1 (a year).
    """

    def total(self, times_per_year=1):
        """
        Returns the income over the specified times_per_year, taking into account
        hours per period for hourly items.

        To calculate `.total()`, an ALIncome must have a `.times_per_year` and `.value`.
        It can also have `.is_hourly` and `.hours_per_period`.
        """
        if hasattr(self, "is_hourly") and self.is_hourly:
            return (
                Decimal(self.value)
                * Decimal(self.hours_per_period)
                * Decimal(self.times_per_year)
            ) / Decimal(times_per_year)
        else:
            return (Decimal(self.value) * Decimal(self.times_per_year)) / Decimal(
                times_per_year
            )


class ALIncomeList(DAList):
    """
    Represents a filterable DAList of incomes-type items. It can make
    use of these item attributes and methods:

    .source
    .owner
    .total()
    .times_per_year
    .value
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if self.object_type is None:
            self.object_type = ALIncome

    def sources(self):
        """Returns a set of the unique sources in the ALIncomeList."""
        sources = set()
        for item in self.elements:
            if hasattr(item, "source"):
                sources.add(item.source)
        return sources

    def matches(self, source):
        """
        Returns an ALIncomeList consisting only of elements matching the specified
        income source, assisting in filling PDFs with predefined spaces. `source`
        may be a list.
        """
        # Always make sure we're working with a list
        sources = source
        if not isinstance(source, list):
            sources = [source]
        # Construct the filtered list
        return ALIncomeList(
            elements=[item for item in self.elements if item.source in sources]
        )

    def total(self, times_per_year=1, source=None, owner=None):
        """
        Returns the total periodic value in the list, gathering the list items
        if necessary. You can optionally filter by `source`. `source` can be a
        string or a list. If you filter by `source` you can also filter by one
        `owner`.

        To calculate `.total()` correctly, all items must have an `.total()`.
        Job-type incomes should automatically exclude deductions.
        """
        self._trigger_gather()
        result = Decimal(0)
        if times_per_year == 0:
            return result
        if source is None:
            for item in self.elements:
                result += Decimal(item.total(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if hasattr(item, "source") and item.source in source:
                    if owner is None:  # if the user doesn't care who the owner is
                        result += Decimal(item.total(times_per_year=times_per_year))
                    else:
                        if (
                            not (isinstance(owner, DAEmpty))
                            and hasattr(item, "owner")
                            and item.owner == owner
                        ):
                            result += Decimal(item.total(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if hasattr(item, "source") and item.source == source:
                    if owner is None:
                        result += Decimal(item.total(times_per_year=times_per_year))
                    else:
                        if (
                            not (isinstance(owner, DAEmpty))
                            and hasattr(item, "owner")
                            and item.owner == owner
                        ):
                            result += Decimal(item.total(times_per_year=times_per_year))
        return result


class ALJob(ALIncome):
    """
    Represents a job that may be hourly or pay-period based. This is a more
    common way of reporting income than ALItemizedJob.
    """

    def gross_total(self, times_per_year=1):
        """
        Same as ALIncome total. Returns the income over the specified times_per_year.
        `times_per_year` is some demoninator of a year. E.g. to express a weekly
        period, use 52. The default is 1 (a year).
        """
        return self.total(times_per_year=times_per_year)

    def net_total(self, times_per_year=1):
        """
        Returns the net income divided by the time times_per_year.
        Only returns a correct total if the job is non-hourly.

        `times_per_year` is some demoninator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        This will force the gathering of the ALJob's `.net` attribute.
        """
        return (Decimal(self.net) * Decimal(self.times_per_year)) / Decimal(
            times_per_year
        )

    def employer_name_address_phone(self):
        """
        Returns name, address and phone number of employer as a string. Forces
        gathering the `.employer`, `.employer_address`, and `.employer_phone`
        attributes.
        """
        return self.employer + ": " + self.employer_address + ", " + self.employer_phone

    def normalized_hours(self, times_per_year=1):
        """
        Returns the number of hours worked in a given times_per_year.
        `times_per_year` is some demoninator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        This will force the gathering of the attributes `.hours_per_period` and
        `.times_per_year`
        """
        return (float(self.hours_per_period) * int(self.times_per_year)) / int(
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

    def total(self, times_per_year=1, source=None):
        """Alias for self.gross_total() to integrate with ALIncomeList math."""
        return self.gross_total(times_per_year=times_per_year, source=source)

    def gross_total(self, times_per_year=1, source=None):
        """
        Returns the sum of the gross incomes of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. `source` can be a
        string or a list.

        `times_per_year` is some demoninator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).
        """
        self._trigger_gather()
        result = Decimal(0)
        if times_per_year == 0:
            return result
        if source is None:
            for job in self.elements:
                result += Decimal(job.gross_total(times_per_year=times_per_year))
        elif isinstance(source, list):
            for job in self.elements:
                if job.source in source:
                    result += Decimal(job.gross_total(times_per_year=times_per_year))
        else:
            for job in self.elements:
                if job.source == source:
                    result += Decimal(job.gross_total(times_per_year=times_per_year))
        return result

    def net_total(self, times_per_year=1, source=None):
        """
        Returns the sum of the net incomes of its ALJobs divided by the time
        times_per_year. You can filter the jobs by `source`. `source` can be a
        string or a list. Only returns a correct total if the job is non-hourly.
        Leaving out `source` will use all sources.

        `times_per_year` is some demoninator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).
        """
        self._trigger_gather()
        result = Decimal(0)
        if times_per_year == 0:
            return result
        if source is None:
            for job in self.elements:
                result += Decimal(job.net_total(times_per_year=times_per_year))
        elif isinstance(source, list):
            for job in self.elements:
                if job.source in source:
                    result += Decimal(job.net_total(times_per_year=times_per_year))
        else:
            for job in self.elements:
                if job.source == source:
                    result += Decimal(job.net_total(times_per_year=times_per_year))
        return result


class ALAsset(ALIncome):
    """Like ALIncome but the `value` attribute is optional."""

    def total(self, times_per_year=1):
        if not hasattr(self, "value") or self.value == "":
            return Decimal(0)
        else:
            return super(ALAsset, self).total(times_per_year=times_per_year)


class ALAssetList(ALIncomeList):
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALAsset

    def total(self, source=None):
        """
        Alias of ALAssetList.market_value() to integrate with ALIncomeList math.
        """
        return self.market_value(source=source)

    def market_value(self, source=None):
        """
        Returns the total `.market_value` of assets in the list. You can filter
        the assets by `source`. `source` can be a string or a list.
        """
        result = Decimal(0)
        for asset in self.elements:
            if source is None:
                result += Decimal(asset.market_value)
            elif isinstance(source, list):
                if asset.source in source:
                    result += Decimal(asset.market_value)
            else:
                if asset.source == source:
                    result += Decimal(asset.market_value)
        return result

    def balance(self, source=None):
        """
        Returns the total `.balance` of assets in the list You can filter
        the assets by `source`. `source` can be a string or a list.
        """
        self._trigger_gather()
        result = Decimal(0)
        for asset in self.elements:
            if source is None:
                result += Decimal(asset.balance)
            elif isinstance(source, list):
                if asset.source in source:
                    result += Decimal(asset.balance)
            else:
                if asset.source == source:
                    result += Decimal(asset.balance)
        return result

    def owners(self, source=None):
        """
        Returns a set of the unique owners of the assets.  You can filter the
        assets by `source`. `source` can be a string or a list.
        """
        owners = set()
        if source is None:
            for asset in self.elements:
                if hasattr(asset, "owner"):
                    owners.add(asset.owner)
        elif isinstance(source, list):
            for asset in self.elements:
                if (
                    hasattr(asset, "owner")
                    and hasattr(asset, "source")
                    and asset.source in source
                ):
                    owners.add(asset.owner)
        else:
            for asset in self.elements:
                if hasattr(asset, "owner") and asset.source == source:
                    owners.add(asset.owner)
        return owners


class ALVehicle(ALAsset):
    """Extends ALAsset. Vehicles have a .year_make_model() method."""

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, "source"):
            self.source = "vehicle"

    def year_make_model(self):
        """
        Returns a string of the format year/make/model of the vehicle. Triggers
        gathering those attributes.
        """
        return self.year + " / " + self.make + " / " + self.model


class ALVehicleList(ALAssetList):
    """
    List of vehicles. Extends ALAssetList. Vehicles have a .year_make_model()
    method.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALVehicle


class ALSimpleValue(DAObject):
    """
    Like a Value object, but no fiddling around with .exists attribute because
    this is designed to be stored in a list, not a dictionary.
    """

    def total(self):
        """
        If desired, to use as a ledger, values can be signed. Setting
        transaction_type = 'expense' makes the value negative. Use min=0 in that
        case.

        This can't be used in an ALIncomeList because its `total` can retrun
        positive and negative values, which would mess up ALIncomeList math
        to add up all positive item amounts.
        """
        if hasattr(self, "transaction_type"):
            return (
                Decimal(self.value * -1)
                if (self.transaction_type == "expense")
                else Decimal(self.value)
            )
        else:
            return Decimal(self.value)

    def __str__(self):
        """Returns own `.total()` as string, not its own name."""
        return str(self.total())


class ALSimpleValueList(DAList):
    """
    Represents a filterable DAList of ALSimpleValues.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALSimpleValue

    def sources(self):
        """
        Returns a set of the unique sources of values stored in the list.
        """
        sources = set()
        for value in self.elements:
            if hasattr(value, "source"):
                sources.add(value.source)
        return sources

    def total(self, source=None):
        """
        Returns the total value in the list, gathering the list items if
        necessary. You can filter the values by `source`. `source` can be a string
        or a list.
        """
        self._trigger_gather()
        result = Decimal(0)
        if source is None:
            for value in self.elements:
                result += Decimal(value.total())
        elif isinstance(source, list):
            for value in self.elements:
                if value.source in source:
                    result += Decimal(value.total())
        else:
            for value in self.elements:
                if value.source == source:
                    result += Decimal(value.total())
        return result


class _ALItemizedValue(DAObject):
    """
    A private class. An item in an ALItemizedJob item list. Here to provide a better
    string value. An object created this way should be accessed directly only to get
    its string. Its values have to be calculated in context of the ALItemizedJob
    that contains it.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)

    def __str__(self):
        """Returns just the name of the object, instead of its whole path."""
        name_end = re.sub(r"^.*\['", "", self.instanceName.split(".")[-1])
        isolated_name = re.sub(r"']$", "", name_end)
        return isolated_name


class _ALItemizedValueDict(DAOrderedDict):
    """
    Dictionary containing both positive and negative values for an ALItemizedJob.
    E.g., wages and deductions being the most common.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = _ALItemizedValue
        if not hasattr(self, "complete_attribute"):
            self.complete_attribute = "value"

    def hook_after_gather(self):
        """
        Update item lists after they've been gathered or edited to remove non-existant
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


class ALItemizedJob(DAObject):
    """
    Represents a job that can have multiple sources of earned income and
    deductions. It may be hourly or pay-period based. This is a less common way
    of reporting income than a plain ALJob.

    Attributes:
    .to_add {_ALItemizedValueDict} Dict of _ALItemizedValues of money coming in.
        Use ALItemizedJob methods to calcuate totals.
    .to_subtract {_ALItemizedValueDict} Dict of _ALItemizedValues of money going out.
        Use ALItemizedJob methods to calcuate totals.
    .times_per_year {str} Actually a number, as a string, of the annual frequency of the
        job.
    .is_hourly {bool} (Optional) Whether the user gets paid hourly for the job.
    .hours_per_period {int} (Optional) If the job is hourly, how many hours the
        user works per period.
    .employer {Individual} (Optional) Individual assumed to have an address and name.

    WARNING: Individual items in `.to_add` and `.to_subtract` should not be used
    directly. They should only be accessed through the methods of this job.

    Fulfills these requirements:
    - A job can be hourly. It's wages will be calcuated with that in mind.
    - Despite an hourly job, some individual items must be calcuated using the
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
        if not hasattr(self, "source") or self.source is None:
            self.source = "Job"
        if not hasattr(self, "employer"):
            self.initializeAttribute("employer", Individual)
        # Money coming in
        if not hasattr(self, "to_add"):
            self.initializeAttribute("to_add", _ALItemizedValueDict)
        # Money being taken out
        if not hasattr(self, "to_subtract"):
            self.initializeAttribute("to_subtract", _ALItemizedValueDict)

    def _item_value_per_times_paid_per_year(self, item, times_per_year=1):
        """
        Given an item and an times_per_year, returns the value accumulated by the
        item for that `times_per_year`.

        `times_per_year` is some demoninator of a year. E.g, to express a weekly
        period, use 52. The default is 1 (a year).

        Args:
        arg item {_ALItemizedValue} Object containing the value and other props
            for an "in" or "out" ALItemizedJob item.
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        """
        if times_per_year == 0:
            return Decimal(0)

        # If an item has its own period, use that instead
        frequency_to_use = self.times_per_year
        if hasattr(item, "times_per_year") and item.times_per_year:
            frequency_to_use = item.times_per_year

        # Both the job and the item itself need to be hourly to be
        # calculated as hourly
        is_hourly = self.is_hourly and hasattr(item, "is_hourly") and item.is_hourly

        # Conform to behavior of docassemble PeriodicValue
        value = Decimal(0)
        if hasattr(item, "value"):
            value = Decimal(item.value)

        # Use the appropriate cacluation
        if is_hourly:
            return (
                value * Decimal(self.hours_per_period) * Decimal(frequency_to_use)
            ) / Decimal(times_per_year)
        else:
            return (value * Decimal(frequency_to_use)) / Decimal(times_per_year)

    def total(self, times_per_year=1, source=None):
        """
        Alias for ALItemizedJob.gross_total to integrate with ALIncomeList math.
        """
        return self.gross_total(times_per_year=times_per_year, source=source)

    def gross_total(self, times_per_year=1, source=None):
        """
        Returns the sum of positive values (payments) for a given times_per_year.
        You can filter the items by `source`. `source` can be a string or a list.
        If you use sources from deductions, they will be ignored.

        Args:
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_add._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in from a source
        for key, value in self.to_add.elements.items():
            if key in sources:
                total += self._item_value_per_times_paid_per_year(
                    value, times_per_year=times_per_year
                )
        return total

    def deduction_total(self, times_per_year=1, source=None):
        """
        Returns the sum of money going out divided by a pay times_per_year as a
        postive value. You can filter the items by `source`. `source` can be a
        string or a list. If you use sources from money coming in, they will be
        ignored.

        Args:
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_subtract._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add all the money going out
        for key, value in self.to_subtract.elements.items():
            if key in sources:
                total += self._item_value_per_times_paid_per_year(
                    value, times_per_year=times_per_year
                )
        return total

    def net_total(self, times_per_year=1, source=None):
        """
        Returns the net (gross minus deductions) value of the job divided by
        `times_per_year`. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        # self.to_add._trigger_gather()
        # self.to_subtract._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in
        for key, value in self.to_add.elements.items():
            if key in sources:
                total += self._item_value_per_times_paid_per_year(
                    value, times_per_year=times_per_year
                )
        # Subtract the money going out
        for key, value in self.to_subtract.elements.items():
            if key in sources:
                total -= self._item_value_per_times_paid_per_year(
                    value, times_per_year=times_per_year
                )
        return total

    def source_to_list(self, source=None):
        """
        Returns list of the job's sources from both the `to_add` and
        `to_subtract`. You can filter the items by `source`. `source` can be a
        string or a list.

        This is mostly for internal use meant to ensure that `source` input is
        always a list.
        """
        sources = []
        # If not filtering by anything, get all possible sources
        if source is None:
            sources = sources + [key for key in self.to_add.elements.keys()]
            sources = sources + [key for key in self.to_subtract.elements.keys()]
        elif isinstance(source, list):
            sources = source
        else:
            sources = [source]
        return sources

    def employer_name_address_phone(self):
        """
        Returns concatenation of employer name and, if they exist, employer
        address and phone number.
        """
        employer_str = self.employer.name
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
            employer_str = f"{ employer_str }: {comma_list( info_list )}"
        return employer_str

    def normalized_hours(self, times_per_year=1):
        """
        Returns the number of hours worked in a times_per_year for an hourly job.
        """
        return round(
            (float(self.hours_per_period) * float(self.times_per_year))
            / float(times_per_year)
        )

class ALItemizedJobList(DAList):
    """
    Represents a list of jobs that can have both payments and money out. This is
    a less common way of reporting income.
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, "source") or self.source is None:
            self.source = "Jobs"
        if self.object_type is None:
            self.object_type = ALItemizedJob

    def total(self, times_per_year=1, source=None):
        """
        Alias for ALItemizedJobList.gross_total to integrate with
        ALIncomeList math.
        """
        return self.gross_total(times_per_year=times_per_year, source=source)

    def gross_total(self, times_per_year=1, source=None):
        """
        Returns the sum of the gross incomes of the list's jobs divided by the
        times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'commissions']
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Add all job gross totals from particular sources
        for job in self.elements:
            total += job.gross_total(times_per_year=times_per_year, source=source)
        return total

    def deduction_total(self, times_per_year=1, source=None):
        """
        Returns the sum of the deductions of the list's jobs divided by the
        times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['taxes', 'dues']
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Add all the money going out for all jobs
        for job in self.elements:
            total += job.deduction_total(times_per_year=times_per_year, source=source)
        return total

    def net_total(self, times_per_year=1, source=None):
        """
        Returns the net of the list's jobs (money in minus money out) divided by
        the times_per_year. You can filter the items by `source`. `source` can be a
        string or a list.

        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'taxes']
        kwarg: times_per_year {str | num} (Optional) Number of times per year you
            want to calcualte. E.g, to express a weekly period, use 52. Default is 1.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Combine all the net incomes in all the jobs from particular sources
        for job in self.elements:
            total += job.net_total(times_per_year=times_per_year, source=source)
        return total
