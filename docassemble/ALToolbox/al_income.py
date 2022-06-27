# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import DAObject, DAList, DAOrderedDict, PeriodicValue, DAEmpty, Individual, comma_list, log, object_name_convert
from decimal import Decimal
import re
import datetime
import docassemble.base.functions
import json


def al_flatten(listname, index=1):
    """
    Return just the nth item in an 2D list. Intended to use for multiple choice
    option lists in Docassemble. e.g., al_flatten(al_asset_source_list()) will
    return ['Savings','Certificate of Deposit'...].
    """
    return [item[index] for item in listname]

def al_income_period_list():
    # Q: Is the current order common? If not, can we do decreasing order?
    """
    Returns a list of lists, each of which contains the number of times a period
    fits into a year and then the English word for that period.
    Example: [12, "Monthly"]
    """
    return [
        [12, "Monthly"],
        [1, "Yearly"],
        [52, "Weekly"],
        [24, "Twice per month"],  # bimonthly?
        [26, "Once every two weeks"],  # fortnightly
        [4, "Once every 3 months"]  # quarterly
    ]

def al_times_per_year(index):
    """
    Given the index of an item in the `al_income_period_list`, returns
    text describing the number of intervals of the given period in a year.
    Example: al_times_per_year(0) will return "Twelve times per year"
    """
    try:
        for row in al_income_period_list():
            if int(index) == int(row[0]):
                return row[1].lower()
        return docassemble.base.functions.nice_number(int(index), capitalize=True) + " " + docassemble.base.functions.word("times per year")
    except:
        return ''
    return ''

docassemble.base.functions.update_language_function('*', 'period_list', al_income_period_list)

def al_recent_years(past=15, order='descending', future=1):
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
    if order=='ascending':
        return list(range(now.year-past, now.year+future, 1))
    else:
        return list(range(now.year+future, now.year-past, -1))

def al_asset_source_list() :
    """Returns a list of asset sources for a multiple choice dropdown."""
    source_list =  DAOrderedDict()
    source_list.auto_gather = False
    source_list.gathered = True
    source_list.elements.update([
        ('savings', 'Savings Account'),
        ('cd', 'Certificate of Deposit'),
        ('ira', 'Individual Retirement Account'),
        ('mutual fund', 'Money or Mutual Fund'),
        ('stocks', 'Stocks or Bonds'),
        ('trust', 'Trust Fund'),
        ('checking', 'Checking Account'),
        ('vehicle', 'Vehicle'),
        ('real estate', 'Real Estate'),
        ('other', 'Other Asset')
    ])
    return source_list

def al_income_source_list() :
    """Returns a dict of income sources for a multiple choice dropdown."""
    source_list = DAOrderedDict()
    source_list['wages'] = 'A job or self-employment'

    source_list.elements.update(al_non_wage_income_list())
    source_list.auto_gather = False
    source_list.gathered = True

    return source_list

def al_non_wage_income_list():
    """Returns a dict of income sources, excluding wages."""
    source_list = DAOrderedDict()
    source_list.auto_gather = False
    source_list.gathered = True
    source_list.elements.update([
        ('SSR', 'Social Security Retirement Benefits'),
        ('SSDI', 'Social Security Disability Benefits'),
        ('SSI', 'Supplemental Security Income (SSI)'),
        ('pension', 'Pension'),
        ('TAFDC', 'TAFDC'),
        ('public assistance', 'Other public assistance'),
        ('SNAP', 'Food Stamps (SNAP)'),
        ('rent', 'Income from real estate (rent, etc)'),
        ('room and board', 'Room and/or Board Payments'),
        ('child support', 'Child Support'),
        ('alimony', 'Alimony'),
        ('other support', 'Other Support'),
        ('other', 'Other')
    ])
    return source_list

def al_expense_source_list() :
    """Returns a dict of expense sources for a multiple choice dropdown."""
    source_list = DAOrderedDict()
    source_list.auto_gather = False
    source_list.gathered = True
    source_list.elements.update([
        ('rent', 'Rent'),
        ('mortgage', 'Mortgage'),
        ('food', 'Food'),
        ('utilities', 'Utilities'),
        ('fuel', 'Other Heating/Cooking Fuel'),
        ('clothing', 'Clothing'),
        ('credit cards', 'Credit Card Payments'),
        ('property tax', 'Property Tax (State and Local)'),
        ('other taxes', 'Other taxes and fees related to your home'),
        ('insurance', 'Insurance'),
        ('medical', 'Medical-Dental (after amount paid by insurance)'),
        ('auto', 'Car operation and maintenance'),
        ('transportation', 'Other transportation'),
        ('charity', 'Church or charitable donations'),
        ('loan payments', 'Loan, credit, or lay-away payments'),
        ('support', 'Support to someone not in household'),
        ('other', 'Other')
    ])
    return source_list


class ALIncome(PeriodicValue):
    """
    Represents an income which may have an hourly rate or a salary. Hourly rate
    incomes must include hours per period. Period is some demoninator of a year
    for compatibility with PeriodicFinancialList class. E.g, to express
    a weekly period, use 52. The default is 1 (a year).
    """
    def total(self, period_to_use=1):
        """
        Returns the income over the specified period_to_use, taking into account
        hours per period for hourly items.

        To calculate `.total()`, an ALIncome must have a `.period` and `.value`.
        It can also have `.is_hourly` and `.hours_per_period`.
        """
        if hasattr(self, 'is_hourly') and self.is_hourly:
            return (Decimal(self.value) * Decimal(self.hours_per_period) * Decimal(self.period)) / Decimal(period_to_use)
        else:
          return (Decimal(self.value) * Decimal(self.period)) / Decimal(period_to_use)


class ALIncomeList(DAList):
    """
    Represents a filterable DAList of incomes-type items. It can make
    use of these item attributes and methods:

    .source
    .owner
    .total()
    .period
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
            if hasattr(item, 'source'):
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
        return ALIncomeList(elements = [item for item in self.elements if item.source in sources])
    
    def total(self, period_to_use=1, source=None, owner=None):
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
        if period_to_use == 0:
            return result
        if source is None:
            for item in self.elements:
                result += Decimal(item.total(period_to_use=period_to_use))
        elif isinstance(source, list):
            for item in self.elements:
                if hasattr(item, 'source') and item.source in source:
                    if owner is None: # if the user doesn't care who the owner is
                        result += Decimal(item.total(period_to_use=period_to_use))
                    else:
                        if not (isinstance(owner, DAEmpty)) and hasattr(item, 'owner') and item.owner == owner:
                            result += Decimal(item.total(period_to_use=period_to_use))
        else:
            for item in self.elements:
                if hasattr(item, 'source') and item.source == source:
                    if owner is None:
                        result += Decimal(item.total(period_to_use=period_to_use))
                    else:
                        if not (isinstance(owner, DAEmpty)) and hasattr(item, 'owner') and item.owner == owner:
                            result += Decimal(item.total(period_to_use=period_to_use))
        return result
    
    def to_json(self):
        """
        Returns the list of incomes as a string, suitable for Legal Server API.
        This will force the gathering of the `.source`, `.period`, and `.value`
        attributes.
        """
        return json.dumps([{
          "source": income.source,
          "frequency": float(income.period),
          "value": income.value
        } for income in self.elements])


class ALJob(ALIncome):
    """
    Represents a job that may be hourly or pay-period based. This is a more
    common way of reporting income than ALItemizedJob.
    """

    def gross_total(self, period_to_use=1):
      """
      Same as ALIncome total. Returns the income over the specified period_to_use.
      `period_to_use` is some demoninator of a year for compatibility with
      PeriodicFinancialList class. E.g. to express a weekly period, use 52. The default
      is 1 (a year).
      """
      return self.total(period_to_use=period_to_use)

    def net_total(self, period_to_use=1):
      """
      Returns the net income divided by the time period_to_use.
      Only returns a correct total if the job is non-hourly.

      `period_to_use` is some demoninator of a year for compatibility with
      PeriodicFinancialList class. E.g, to express a weekly period, use 52. The
      default is 1 (a year).

      This will force the gathering of the ALJob's `.net` attribute.
      """
      return (Decimal(self.net) * Decimal(self.period)) / Decimal(period_to_use)

    def employer_name_address_phone(self):
        """
        Returns name, address and phone number of employer as a string. Forces
        gathering the `.employer`, `.employer_address`, and `.employer_phone`
        attributes.
        """
        return self.employer + ': ' + self.employer_address + ', ' + self.employer_phone

    def normalized_hours(self, period_to_use=1):
        """
        Returns the number of hours worked in a given period_to_use. 
        `period_to_use` is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express a weekly period, use 52. The
        default is 1 (a year).

        This will force the gathering of the attributes `.hours_per_period` and
        `.period`
        """
        return (float(self.hours_per_period) * int(self.period)) / int(period_to_use)


class ALJobList(ALIncomeList):
    """
    Represents a list of ALJobs. Adds the `.gross_total()` and
    `.net_total()` methods to the ALIncomeList class. It's a more common
    way of reporting income than ALItemizedJobList.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALJob
    
    def total(self, period_to_use=1, source=None):
      """Alias for self.gross_total() to integrate with ALIncomeList math."""
      return self.gross_total(period_to_use=period_to_use, source=source)
    
    def gross_total(self, period_to_use=1, source=None):
        """
        Returns the sum of the gross incomes of its ALJobs divided by the time
        period_to_use. You can filter the jobs by `source`. `source` can be a
        string or a list.

        `period_to_use` is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express a weekly period, use 52. The
        default is 1 (a year).
        """
        self._trigger_gather()
        result = Decimal(0)
        if period_to_use == 0:
            return result
        if source is None:
            for job in self.elements:
                result += Decimal(job.gross_total(period_to_use=period_to_use))
        elif isinstance(source, list):
            for job in self.elements:
                if job.source in source:
                    result += Decimal(job.gross_total(period_to_use=period_to_use))
        else:
            for job in self.elements:
                if job.source == source:
                    result += Decimal(job.gross_total(period_to_use=period_to_use))
        return result
    
    def net_total(self, period_to_use=1, source=None):
        """
        Returns the sum of the net incomes of its ALJobs divided by the time
        period_to_use. You can filter the jobs by `source`. `source` can be a
        string or a list. Only returns a correct total if the job is non-hourly.
        Leaving out `source` will use all sources.

        `period_to_use` is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express a weekly period, use 52. The
        default is 1 (a year).
        """
        self._trigger_gather()
        result = Decimal(0)
        if period_to_use == 0:
            return result
        if source is None:
            for job in self.elements:
                result += Decimal(job.net_total(period_to_use=period_to_use))
        elif isinstance(source, list):
            for job in self.elements:
                if job.source in source:
                    result += Decimal(job.net_total(period_to_use=period_to_use))
        else:
            for job in self.elements:
                if job.source == source:
                    result += Decimal(job.net_total(period_to_use=period_to_use))
        return result


class ALAsset(ALIncome):
    """Like ALIncome but the `value` attribute is optional."""
    def total(self, period_to_use=1):
      if not hasattr(self, 'value') or self.value == '':
        return Decimal(0)
      else:
        return super(ALAsset, self).total(period_to_use=period_to_use)


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
        owners=set()
        if source is None:
            for asset in self.elements:
                if hasattr(asset, 'owner'):
                    owners.add(asset.owner)
        elif isinstance(source, list):
            for asset in self.elements:
                if hasattr(asset, 'owner') and hasattr(asset, 'source') and asset.source in source:
                    owners.add(asset.owner)
        else:
            for asset in self.elements:
                if hasattr(asset,'owner') and asset.source == source:
                    owners.add(asset.owner)
        return owners


class ALVehicle(ALAsset):
    """Extends ALAsset. Vehicles have a .year_make_model() method."""
    def init(self, *pargs, **kwargs):
      super().init(*pargs, **kwargs)
      if not hasattr(self, 'source'):
        self.source = 'vehicle'
      
    def year_make_model(self):
        """
        Returns a string of the format year/make/model of the vehicle. Triggers
        gathering those attributes.
        """
        return self.year + ' / ' + self.make + ' / ' + self.model


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
        if hasattr(self, 'transaction_type'):
            return Decimal(self.value * -1) if (self.transaction_type == 'expense') else Decimal(self.value)
        else:
            return Decimal(self.value)

    def __str__(self):
        """Returns own `.total()` as string, not its own name."""
        return str(self.total())


class ALValueList(DAList):
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
            if hasattr(value, 'source'):
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


class ALLedger(ALValueList):
    """
    Represents an account ledger. Adds .running_total() method which adds a
    `running_total` attribute to each ledger entry.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)              

    def running_total(self):
        """
        Sort the ledger by date, then add a .running_total to each ledger entry.
        """
        self.elements.sort(key=lambda y: y.date)
        running_total = Decimal(0)
        for entry in self.elements:
            running_total += Decimal(entry.total())
            entry.running_total = Decimal(running_total)


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
    name_end = re.sub( r"^.*\['", '', self.instanceName.split(".")[-1] )
    isolated_name = re.sub( r"']$", '', name_end )
    return isolated_name


class ALItemizedValueDict(DAOrderedDict):
  """
  Contains values going into or coming out of ALItemizedJobs. Also manages hooks
  to update items when they've been gathered or edited. E.g. removing non-existent
  items.
  """
  def init(self, *pargs, **kwargs):
    super().init(*pargs, **kwargs)
    self.object_type = _ALItemizedValue
    if not hasattr(self, 'complete_attribute'):
        self.complete_attribute = 'value'
    
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
      if hasattr(value, 'exists') and value.exists is False:
        keys_to_delete.append( key )
    # Delete the keys
    for key in keys_to_delete:
      self.delitem( key )
      

class ALItemizedJob(DAObject):
    """
    Represents a job that can have multiple sources of earned income and
    deductions. It may be hourly or pay-period based. This is a less common way
    of reporting income than a plain ALJob.
    
    Attributes:
    .in_values {ALItemizedValueDict} Dict of _ALItemizedValues of money coming in.
        Use ALItemizedJob methods to calcuate totals.
    .out_values {ALItemizedValueDict} Dict of _ALItemizedValues of money going out.
        Use ALItemizedJob methods to calcuate totals.
    .period {str} Actually a number, as a string, of the annual frequency of the
        job.
    .is_hourly {bool} (Optional) Whether the user gets paid hourly for the job.
    .hours_per_period {int} (Optional) If the job is hourly, how many hours the
        user works per period.
    .employer {Individual} (Optional) Individual assumed to have an address and name.
    
    WARNING: Individual items in `.in_values` and `.out_values` should not be used
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
        if not hasattr(self, 'source') or self.source is None:
            self.source = 'Job'
        if not hasattr(self, 'employer'):
          self.initializeAttribute('employer', Individual)
        # Money coming in
        if not hasattr(self, 'in_values'):
          self.initializeAttribute('in_values', ALItemizedValueDict)
        # Money being taken out
        if not hasattr(self, 'out_values'):
          self.initializeAttribute('out_values', ALItemizedValueDict)
    
    def item_value_per_period(self, item, period_to_use=1):
        """
        Given an item and an period_to_use, returns the value accumulated by the
        item for that `period_to_use`.

        `period_to_use` is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express a weekly period, use 52. The
        default is 1 (a year).
        
        Args:
        arg item {_ALItemizedValue} Object containing the value and other props
            for an "in" or "out" ALItemizedJob item.
        kwarg: period_to_use {str | num} (Optional) Default is 1. Some
            demoninator of a year for compatibility with PeriodicFinancialList
            class. E.g, to express a weekly period, use 52.
        """
        if period_to_use == 0:
          return Decimal(0)

        period = self.period
        if hasattr(item, 'period') and item.period:
          period = item.period

        is_hourly = False
        # Override if item should be calculated hourly (like wages)
        if self.is_hourly and hasattr(item, 'is_hourly'):
          is_hourly = item.is_hourly

        # Conform to behavior of docassemble PeriodicValue
        value = Decimal(0)
        if hasattr(item, 'value'):
          value = Decimal(item.value)

        # Use the appropriate cacluation
        if is_hourly:
          return (value * Decimal(self.hours_per_period) * Decimal(period)) / Decimal(period_to_use)
        else:
          return (value * Decimal(period)) / Decimal(period_to_use)
    
    def total(self, period_to_use=1, source=None):
        """
        Alias for ALItemizedJob.gross_total to integrate with ALIncomeList math.
        """
        return self.gross_total(period_to_use=period_to_use, source=source)
    
    def gross_total(self, period_to_use=1, source=None):
        """
        Returns the sum of positive values (payments) for a given period_to_use.
        You can filter the items by `source`. `source` can be a string or a list.
        If you use sources from deductions, they will be ignored.
        
        Args:
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        #self.in_values._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in from a source
        for key, value in self.in_values.elements.items():
          if key in sources:
            total += self.item_value_per_period(value, period_to_use=period_to_use)
        return total
    
    def deduction_total(self, period_to_use=1, source=None):
        """
        Returns the sum of money going out divided by a pay period_to_use as a
        postive value. You can filter the items by `source`. `source` can be a
        string or a list. If you use sources from money coming in, they will be
        ignored.
        
        Args:
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        #self.out_values._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add all the money going out
        for key, value in self.out_values.elements.items():
          if key in sources:
            total += self.item_value_per_period(value, period_to_use=period_to_use)
        return total
    
    def net_total(self, period_to_use=1, source=None):
        """
        Returns the net (gross minus deductions) value of the job divided by
        `period_to_use`. You can filter the items by `source`. `source` can be a
        string or a list.
        
        Args:
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        kwarg: source {str | [str]} (Optional) Source or list of sources of desired
            item(s).
        """
        #self.in_values._trigger_gather()
        #self.out_values._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in
        for key, value in self.in_values.elements.items():
          if key in sources:
            total += self.item_value_per_period(value, period_to_use=period_to_use)
        # Subtract the money going out
        for key, value in self.out_values.elements.items():
          if key in sources:
            total -= self.item_value_per_period(value, period_to_use=period_to_use)
        return total
    
    def source_to_list(self, source=None):
        """
        Returns list of the job's sources from both the `in_values` and
        `out_values`. You can filter the items by `source`. `source` can be a
        string or a list.
        
        This is mostly for internal use meant to ensure that `source` input is
        always a list.
        """
        sources = []
        # If not filtering by anything, get all possible sources
        if source is None:
          sources = sources + [key for key in self.in_values.elements.keys()]
          sources = sources + [key for key in self.out_values.elements.keys()]
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
        has_address = hasattr( self.employer.address, 'address' ) and self.employer.address.address
        has_number = hasattr( self.employer, 'phone_number' ) and self.employer.phone_number
        # Create a list so we can take advantage of `comma_list` instead
        # of doing further fiddly list manipulation
        if has_address:
          info_list.append( self.employer.address.on_one_line() )
        if has_number:
          info_list.append( self.employer.phone_number )
        # If either exist, add a colon and the appropriate strings
        if has_address or has_number:
          employer_str = f'{ employer_str }: {comma_list( info_list )}'
        return employer_str
    
    def normalized_hours(self, period_to_use=1):
        """
        Returns the number of hours worked in a period_to_use for an hourly job.
        """
        return round((float(self.hours_per_period) * float(self.period)) / float(period_to_use))

    #def to_json(self):
    #    """
    #    Returns an itemized job's dictionary as JSON.
    #    # Q: I couldn't find Legal Server's API for this. Link? Does this need to be a string? If so, how do we handle this with .to_json of itemized job list?
    #    """
    #    return {
    #      "name": self.name,
    #      "frequency": float(self.period),
    #      "gross": float(self.gross_total(period_to_use=self.period)),
    #      "net": float(self.net_total(period_to_use=self.period)),
    #      "in_values": self.values_json(self.in_values),
    #      "out_values": self.values_json(self.out_values)
    #    }
    #
    #def values_json(self, values_dict):
    #    """
    #    Return a JSON version of the given dict of ALItemizedJob "in" or "out"
    #    objects.
    #    """
    #    result = {}
    #    for key in values_dict.true_values():
    #      value = values_dict[key]
    #      result[key] = {}
    #      result[key]['value'] = value.value
    #      # Q: Include defaults for all attributes?
    #      if hasattr(value, 'is_hourly'):
    #        result[key]['is_hourly'] = value.is_hourly
    #      if hasattr(value, 'period'):
    #        result[key]['period'] = value.period
    #    return result


class ALItemizedJobList(DAList):
    """
    Represents a list of jobs that can have both payments and money out. This is
    a less common way of reporting income.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, 'source') or self.source is None:
            self.source = 'Jobs'
        if self.object_type is None:
            self.object_type = ALItemizedJob
    
    def total(self, period_to_use=1, source=None):
        """
        Alias for ALItemizedJobList.gross_total to integrate with
        ALIncomeList math.
        """
        return self.gross_total(period_to_use=period_to_use, source=source)
    
    def gross_total(self, period_to_use=1, source=None):
        """
        Returns the sum of the gross incomes of the list's jobs divided by the
        period_to_use. You can filter the items by `source`. `source` can be a
        string or a list.
        
        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'commissions']
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
            return total
        # Add all job gross totals from particular sources
        for job in self.elements:
          total += job.gross_total(period_to_use=period_to_use, source=source)
        return total
    
    def deduction_total(self, period_to_use=1, source=None):
        """
        Returns the sum of the deductions of the list's jobs divided by the
        period_to_use. You can filter the items by `source`. `source` can be a
        string or a list.
        
        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['taxes', 'dues']
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
          return total
        # Add all the money going out for all jobs
        for job in self.elements:
          total += job.deduction_total(period_to_use=period_to_use, source=source)
        return total
    
    def net_total(self, period_to_use=1, source=None):
        """
        Returns the net of the list's jobs (money in minus money out) divided by
        the period_to_use. You can filter the items by `source`. `source` can be a
        string or a list.
        
        Args:
        kwarg: source {str | [str]} - (Optional) Source or list of sources of
            desired job items to sum from every itemized job.
            E.g. ['tips', 'taxes']
        kwarg: period_to_use {str | num} (Optional) Number of times per year the
            period occurs. E.g, to express a weekly period, use 52. Default is 1.
            Used for compatibility with PeriodicFinancialList class.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period_to_use == 0:
            return total
        # Combine all the net incomes in all the jobs from particular sources
        for job in self.elements:
          total += job.net_total(period_to_use=period_to_use, source=source)
        return total
    
    #def to_json(self):
    #    """Returns a list of jobs as JSON."""
    #    return [job.to_json() for job in self.elements]
