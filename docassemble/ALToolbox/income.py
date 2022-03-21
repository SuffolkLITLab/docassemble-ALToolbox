# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import DAObject, DAList, DAOrderedDict, PeriodicValue, DAEmpty, Individual, comma_list, log
from decimal import Decimal
import datetime
import docassemble.base.functions
import json


def flatten(listname,index=1):
    """
    Return just the nth item in an 2D list. Intended to use for multiple choice
    option lists in Docassemble. e.g., flatten(asset_source_list()) will return
    ['Savings','Certificate of Deposit'...].
    """
    return [item[index] for item in listname]

def income_period_list():
    # Q: Is the current order common? If not, can we do decreasing order?
    return [
        [12,"Monthly"],
        [1,"Yearly"],
        [52,"Weekly"],
        [24,"Twice per month"],  # bimonthly?
        [26,"Once every two weeks"],  # fortnightly
        [4,"Once every 3 months"]  # quarterly
    ]

def income_period(index):
    # Q: Name: income_period_description?
    """
    Returns text describing the number of intervals of the period in a year.
    """
    try:
        for row in income_period_list():
            if int(index) == int(row[0]):
                return row[1].lower()
        return docassemble.base.functions.nice_number(int(index), capitalize=True) + " " + docassemble.base.functions.word("times per year")
    except:
        return ''
    return ''

docassemble.base.functions.update_language_function('*', 'period_list', income_period_list)

def recent_years(years=15, order='descending',future=1):
    """
    Returns a list of the most recent years, continuing into the future.
    Defaults to most recent 15 years+1. Useful to populate a combobox of years
    where the most recent ones are most likely. E.g. automobile years or
    birthdate. Keyword paramaters: years, order (descending or ascending),
    future (defaults to 1).
    """
    now = datetime.datetime.now()
    if order=='ascending':
        return list(range(now.year-years,now.year+future,1))
    else:
        return list(range(now.year+future,now.year-years,-1))

def asset_source_list() :
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

def income_source_list() :
    """Returns a dict of income sources for a multiple choice dropdown."""
    source_list = DAOrderedDict()
    source_list['wages'] = 'A job or self-employment'

    source_list.elements.update(non_wage_income_list())
    source_list.auto_gather = False
    source_list.gathered = True

    return source_list

def non_wage_income_list():
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

def expense_source_list() :
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
    incomes must include hours and period. Period is some demoninator of a year
    for compatibility with PeriodicFinancialList class. E.g, to express
    hours/week, use 52.
    """
    # Q: It's actually the value per period. "amount" isn't super clear. Change name?
    def amount(self, period=1):
        """Returns the income over the specified period."""
        ## Q: Conform to behavior of docassemble PeriodicValue?
        #if not hasattr(self, 'value'):
        #  return Decimal(0)
        if hasattr(self, 'is_hourly') and self.is_hourly:
            return Decimal(self.hourly_rate * self.hours_per_period * self.period) / Decimal(period)
        else:
          return (Decimal(self.value) * Decimal(self.period)) / Decimal(period)


# Q: Make income list so it can add up all income sources (jobs, assets, etc?)
class ALIncomeList(DAList):
    """
    Represents a filterable DAList of income items, each of which has an
    associated period or hourly wages.
    # Q: Give everything (inc. jobs) an `.amount()`. For jobs, it would be equivalent to .net_amount()
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.elements = list()
        if not hasattr(self, 'object_type'):
            self.object_type = ALIncome
    
    def sources(self):
        """Returns a set of the unique sources of values stored in the list."""
        sources = set()
        for item in self.elements:
            if hasattr(item, 'source'):
                sources.add(item.source)
        return sources

    # Q: Instead, require `source` to always be a list? They just have
    # to put brackets around the item at worst. Same question for all
    # other locations.
    def matches(self, source):
        """
        Returns an ALIncomeList consisting only of elements matching the
        specified ALIncome source, assisting in filling PDFs with predefined
        spaces. `source` may be a list.
        """
        # Always make sure we're working with a list
        sources = source
        if not isinstance(source, list):
            sources = [source]
        return ALIncomeList(elements = [item for item in self.elements if item.source in sources])
    
    # Names: .total() -> .total_amount() since it uses an annual frequency (unlike ValueList)?
    def total(self, period=1, source=None, owner=None):
        """
        Returns the total periodic value in the list, gathering the list items
        if necessary. You can specify a `source`, which may be a list, to only
        add entries of the matching source. If you specify the `source` you can
        also specify one `owner`.
        """
        # Q: can `owner` be a list? I see that `.owners()` returns a set
        self._trigger_gather()
        result = Decimal(0)
        if period == 0:
            return result
        if source is None:
            # Q: Should this allow the user to filter _just_ by the `owner`
            # as well if they include just the `owner`?
            for item in self.elements:
                result += Decimal(item.amount(period=period))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    if owner is None: # if we don't care who the owner is
                        result += Decimal(item.amount(period=period))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(period=period))
        else:
            for item in self.elements:
                if item.source == source:
                    if owner is None:
                        result += Decimal(item.amount(period=period))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(period=period))
        return result
    
    def to_json(self):
        """Returns an income list suitable for Legal Server API."""
        return [{
          "source": income.source,
          # Q: Should `frequency` be `period`?
          "frequency": float(income.period),
          # Q: shouldn't this use `amount()`? [what does this second question mean? ->] Is this why period needs to default to 1?
          # Q: Actually, in docassemble, `.amount()` always defaults to a period of 1, so if this is `amount`, it would use a year as a period, so maybe this really should be called `value` instead.
          "value": income.value
        } for income in self.elements]


class ALJob(ALIncome):
    """
    Represents a job that may be hourly or pay-period based. If non-hourly, may
    specify gross and net income amounts. This is a more common way of reporting
    income than ALItemizedJob.
    """
    def gross_amount(self, period=1):
      """Gross amount is identical to ALIncome amount."""
      return self.amount(period=period)
    
    # Q: Not sure of the name, but something like `net_value` or
    # `net_amount` seems indistinguishable from `.net`. Maybe
    # there should be `payment` and `deductions` and `.net()`
    # like ALItemizedJob
    def net_amount(self, period=1):
      """
      Returns the net amount provided by the user (e.g. money in minus money
      out) for the time period given. Only applies if value is non-hourly.
      Period is some demoninator of a year for compatibility with
      PeriodicFinancialList class. E.g, to express hours/week, use 52.
      """
      return (Decimal(self.net) * Decimal(self.period)) / Decimal(period)

    def employer_name_address_phone(self):
        """Returns name, address and phone number of employer."""
        return self.employer + ': ' + self.employer_address + ', ' + self.employer_phone

    def normalized_hours(self, period):
        """Returns the number of hours worked in a given period."""
        return (float(self.hours_per_period) * int(self.period)) / int(period)


class ALJobList(ALIncomeList):
    """
    Represents a list of ALJobs. Adds the `.net_amount()` and `.gross_amount()`
    methods to the ALIncomeList class. It's a more common way of reporting
    income as opposed to ALItemizedJobList.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALJob
    
    def gross_amount(self, period=1, source=None):
        """
        Gross amount is identical to ALIncome amount, except it adds up all
        ALJobs it contains and filters them by `source`, which can be a string
        or a list.
        """
        self._trigger_gather()
        result = 0
        if period == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.gross_amount(period=period))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.gross_amount(period=period))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.gross_amount(period=period))
        return result
    
    def net_amount(self, period=1, source=None):
        """
        Returns the net amount provided by the user (e.g. money in minus money
        out) for the time period given for all jobs of the given `source` which
        can be a string or a list. Only applies if value is non-hourly. Period
        is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express hours/week, use 52.
        """
        self._trigger_gather()
        result = 0
        if period == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.net_amount(period=period))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.net_amount(period=period))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.net_amount(period=period))
        return result


class _ALItemizedValue(DAObject):
  """
  A private class. An item in an ALItemizedJob item list. Here to provide a better
  string value. An object created this way should only be accessed directly to get
  its string. Its `amounts` have to be calculated in context of the ALItemizedJob
  that contains it.
  """
  def init(self, *pargs, **kwargs):
    super().init(*pargs, **kwargs)

  def __str__(self):
    """Return just the name of the object, instead of its whole path."""
    # Q: How does this string value have access to the names of its containers? And is it possible to get other information about its containers in a similar way?
    # Also, there must be a better way to do this, right?
    orig_name = self.object_name()
    new_name = orig_name.replace( 'out values in the itemized job', '' )
    new_name = new_name.replace( 'in values in the itemized job', '' )
    return new_name


class ALItemizedJob(DAObject):
    """
    Represents a job that can have multiple sources of earned income and
    deductions. It may be hourly or pay-period based. This is a less common way
    of reporting income than a plain ALJob.
    
    attribs:
    .period {str} Actually a number, as a string, of the annual frequency of the
        job.
    .is_hourly {bool} Whether the user gets paid hourly for the job.
    .hours_per_period {int} If the job is hourly, how many hours the user works
        per period.
    .employer {Individual} Individual assumed to have an address and name.
    .in_values {DAOrderedDict} Dict of _ALItemizedValues of money coming in. Use
        ALItemizedJob methods to calcuate amounts.
    .out_values {DAOrderedDict} Dict of _ALItemizedValues of money going out.
        Use ALItemizedJob methods to calcuate amounts.
    """
    """
    Notes:
    # Q: Has these in common with ALIncomeList: .total(), .to_json(). I don't want to provide individual items with .matches() because directly using individual items themselves should be avoided. Only their str() and .value is reliable. ALItemizedJob methods should be used for other needs.
    
    # Look at needs in SSI interview (https://github.com/nonprofittechy/docassemble-ssioverpaymentwaiver)
    # `amount` is in docassemble. not sure it means quite the same thing. period doesn't quite either.
    
    Names and explanations of job in/out sources
    # in: commission, bonus, hourly wage (wages?), non-hourly wages (salary?), overtime, tips
    # out: deductions(?), garnishments, dues, insurance, federal taxes, state taxes
    # https://fingercheck.com/the-difference-between-a-paycheck-and-a-pay-stub/
    # "Deductions" definition: the amounts subtracted or withheld from the total pay, including the income tax percentage of an employee’s gross wages.
    # Social security and Medicare are deducted based on the income over the set threshold.
    # Other deductions can include state and local income taxes, employee 401K contributions, insurance payments, profit sharing, union dues, garnishments and unemployment insurance etc.
    """
    """
    Requirements:
    Implemented:
    - A job can be hourly
    - Despite an hourly job, some individual items must be calcuated
      using the whole period
    - Some items will have their own periods
    - Devs need to be able to have different types of job base_pay (e.g.
      full time, part time) that they must be able to access separately
    - Devs may need to total amounts same names across different jobs (e.g.
      tips for all jobs, etc.)
    - need total in/income and total out/deductions
    - Users must be able to add arbitrary in/out items for a job
    Unsure:
    - get jobs by attributes, total by job attribute. devs can do this themselves by:
        da filter by attribute (raises exception)
        list comprehension
        Unclear if this is to get line_item in all jobs or to get jobs themselves by attribute. Think this was one of the "part time" vs. "full time" conversations.
    # Q: Allow multiple "sources" per item, so an item can be both "taxes" and "federal taxes"? Devs can always filter the names themselves, so maybe not MVP
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        if not hasattr(self, 'employer'):
          self.initializeAttribute('employer', Individual)
        # Q: Use complete_attribute = "value" for in/out items?
        # Money coming in
        # Names: in_values -> values_in, money_in, income, incomes
        if not hasattr(self, 'in_values'):
          self.initializeAttribute('in_values', DAOrderedDict.using(object_type=_ALItemizedValue))
        # Money being taken out
        # Names: in_values -> values_out, money_out, deductions ("an amount that you can use to reduce your income-tax liability")
        if not hasattr(self, 'out_values'):
          self.initializeAttribute('out_values', DAOrderedDict.using(object_type=_ALItemizedValue))
    
    # Names: change .period to .frequency or .annual_frequency? Or job has a period while asking for `amount` has a frequency?
    # Names: divided_by = 52, annual_frequency=52/desired_frequency
    # Q: Allow `line_item`/`item` to be a string (source/id name)?
    # Names: line_item_period_value? item_period_value?
    def item_amount(self, item, period=1):
        """
        Given an item and an period, returns the value accumulated
        by the item for that period.
        
        params
        arg item {_ALItemizedValue} Object containing the value and other props
            for an "in" or "out" ALItemizedJob item.
        kwarg period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        """
        if period == 0:
          return Decimal(0)

        own_period = self.period
        if hasattr(item, 'period') and item.period:
          own_period = item.period

        is_hourly = False
        # Override if item should be calculated hourly (like wages)
        # Names: is_hourly -> calculate_hourly (for individual items)
        if self.is_hourly and hasattr(item, 'is_hourly'):
          is_hourly = item.is_hourly

        # Conform to behavior of docassemble PeriodicValue
        value = Decimal(0)
        if hasattr(item, 'value'):
          value = Decimal(item.value)

        # Use the appropriate cacluation
        if is_hourly:
          return (value * Decimal(self.hours_per_period) * Decimal(own_period)) / Decimal(period)
        else:
          return (value * Decimal(own_period)) / Decimal(period)
    
    # Q: What aliases would be useful? We need gross and incomes, apparently. What else?
    # ---
    # In amount aliases
    # ---
    def total_in(self, period=1, source=None):
        """Alias for ALItemizedJob.gross_amount."""
        return self.gross_amount(period=period, source=source)
    def in_amount(self, period=1, source=None):
        """Alias for ALItemizedJob.gross_amount."""
        return self.gross_amount(period=period, source=source)
    def incomes(self, period=1, source=None):
        """Alias for ALItemizedJob.gross_amount."""
        return self.gross_amount(period=period, source=source)
    
    # ---
    # Out amount aliases
    # ---
    def out_amount(self, period=1, source=None):
        """Alias for ALItemizedJob.total_out()."""
        return self.total_out(period=period, source=source)
    def deductions(self, period=1, source=None):
        """
        Alias for ALItemizedJob.total_out()
        "Deductions" in the wrong word. In financial vocabulary, it technically
        means amounts you can use to reduce your income-tax liability.
        """
        return self.total_out(period=period, source=source)
    
    # ---
    # Net aliases
    # ---
    def total(self, period=1, source=None):
        """Alias for ALItemizedJob.net_amount()."""
        return self.net_amount(period=period, source=source)
    def total_amount(self, period=1, source=None):
        """Alias for ALItemizedJob.net_amount()."""
        return self.net_amount(period=period, source=source)
    
    # ---
    # Actual calculations
    # ---
    # Include filtering by name? So confused.
    def gross_amount(self, period=1, source=None):
        """
        Returns the sum of positive values (payments) for a given pay period (1
        for yearly, 12 for monthly, etc). Default frequency value of 1 (yearly)
        so jobs/items can be normalized to each other easily (instead of using
        their own periods by default).
        
        params
        kwarg period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        kwarg source {str or [str]} Name or list of names of desired item(s).
        """
        #self._trigger_gather()
        #self.in_values._trigger_gather()
        total = Decimal(0)
        if period == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in from a source
        for key, item in self.in_values.elements.items():
          if key in sources:
            total += self.item_amount(item, period=period)
        return total
    
    def total_out(self, period=1, source=None):
        """
        Returns the sum of negative values for a given pay period (1 for yearly,
        12 for monthly, etc). Default frequency value of 1 (yearly) so
        jobs/items can be normalized to each other easily (instead of using
        their own periods by default).
        
        params
        kwarg period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        kwarg source {str or [str]} Name or list of names of desired item(s).
        """
        total = Decimal(0)
        if period == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add all the money going out
        for key, item in self.out_values.elements.items():
          if key in sources:
            total += self.item_amount(item, period=period)
        return total
    
    def net_amount(self, period=1, source=None):
        """
        Returns the net (payments minus deductions) value of the job for a given
        pay period (1 for yearly, 12 for monthly, etc). Default frequency value
        of 1 so all jobs can be normalized.
        
        params
        kwarg period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        kwarg source {str or [str]} Name or list of names of desired item(s).
        """
        # Cannot trigger gather for DAObject?
        #self._trigger_gather()
        #self.in_values._trigger_gather()
        #self.out_values._trigger_gather()
        total = Decimal(0)
        if period == 0:
          return total
        # Make sure we're always working with a list of sources (names?)
        sources = self.source_to_list(source=source)
        # Add up all money coming in
        for key, item in self.in_values.elements.items():
          if key in sources:
            total += self.item_amount(item, period=period)
        # Subtract the money going out
        for key, item in self.out_values.elements.items():
          if key in sources:
            total -= self.item_amount(item, period=period)
        return total
    
    # Q: Should this be `name`, like an itemized job's name?
    # Different signature to ALIncomeList `sources`
    def source_to_list(self, source=None):
        """
        Given a string or list of strings, return a list of strings. If no
        strings given, return a list of all keys in both the `in_values` and
        `out_values` _ALItemizedValues.
        """
        # If not filtering by anything, get all possible sources
        sources = []
        if source is None:
          sources = sources + [key for key in self.in_values.elements.keys()]
          sources = sources + [key for key in self.out_values.elements.keys()]
        elif isinstance(source, list):
          sources = source
        else:
          sources = [source]
        return sources
    
    ## Names: Should `source` be `id`? That only makes sense for jobs, not incomes/assets, so they then won't share an interface. Maybe `name`? Or do we need categories, not `id`s? In what situations would there be income values from the same "type"/`source`?
    # Q/Names: Should `period` be a string that's the "name" of the period? Calling it just `period` is a bit confusing when the value is a number. e.g. `period = 12`, to me, doesn't shout out "monthly".
    
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
    
    def normalized_hours(self, period):
        """
        Returns the number of hours worked in a given period for an hourly job.
        """
        # Q: Is there a safe value to return if it's not hourly?
        return round((float(self.hours_per_period) * float(self.period)) / float(period))
    
    # Name: to_json_string? json.dumps returns str right? Don't we want to just give them a JSON-compatible dict and let them prety print it their own way?
    def to_json(self):
        """
        Returns an itemized job's dictionary suitable for Legal Server API.
        # Q: I couldn't find Legal Server's API for this. Link? Does this need to be a string? If so, how do we handle this with .to_json of itemized job list?
        """
        return {
          "name": self.name,
          "frequency": float(self.period),
          "gross": float(self.gross_amount(period=self.period)),
          "net": float(self.net_amount(period=self.period)),
          "in_values": self.items_json(self.in_values),
          "out_values": self.items_json(self.out_values)
        }
    
    def items_json(self, item_dict):
        """
        Return a JSON version of the given dict of ALItemizedJob "in" or "out"
        objects.
        """
        result = {}
        for key in item_dict.true_values():
          item = item_dict[key]
          result[key] = {}
          result[key]['value'] = item.value
          # Q: Include defaults for all attributes?
          if hasattr(item, 'is_hourly'):
            result[key]['is_hourly'] = item.is_hourly
          if hasattr(item, 'period'):
            result[key]['period'] = item.period
        return result


class ALItemizedJobList(DAList):
    """
    Represents a list of jobs that can have both payments and money out. This is
    a less common way of reporting income.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALItemizedJob
    
    # Q: Do we want some way to have a running total?
    # ---
    # In amount aliases
    # ---
    def total_in(self, period=1, source=None):
        """Alias for ALItemizedJobList.gross_amount()."""
        return self.gross_amount(period=period, source=source)
    def in_amount(self, period=1, source=None):
        """Alias for ALItemizedJobList.gross_amount()."""
        return self.gross_amount(period=period, source=source)
    def incomes(self, period=1, source=None):
        """Alias for ALItemizedJobList.gross_amount()."""
        return self.gross_amount(period=period, source=source)
      
    # ---
    # Out amount aliases
    # ---
    def out_amount(self, period=1, source=None):
        """Alias for ALItemizedJobList.total_out()."""
        return self.total_out(period=period, source=source)
    def deductions(self, period=1, source=None):
        """
        Alias for ALItemizedJobList.total_out()
        "Deductions" in the wrong word. In financial vocabulary, it technically
        means amounts you can use to reduce your income-tax liability.
        """
        return self.total_out(period=period, source=source)
    
    # ---
    # Net aliases
    # ---
    def total(self, period=1, source=None):
        """Alias for ALItemizedJobList.net_amount()."""
        return self.net_amount(period=period, source=source)
    def total_amount(self, period=1, source=None):
        """Alias for ALItemizedJobList.net_amount()."""
        return self.net_amount(period=period, source=source)
    
    # ---
    # Actual calculations
    # ---
    def gross_amount(self, period=1, source=None):
        """
        Return amount totals of money coming in for a specific source or sources
        calculated using the desired annual frequency (monthly = 12 times per
        year, etc).
        
        @params
        kwarg: source {str, [str]} - Name or list of names of desired item(s) to
            sum from every itemized job. E.g. ['tips', 'taxes']
        kwarg: period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period == 0:
            return total
        # Add all job gross amounts from particular sources
        for job in self.elements:
          total += job.gross_amount(period=period, source=source)
        return total
    
    def total_out(self, period=1, source=None):
        """
        Return amount totals of money going out for a specific source or sources
        calculated using the desired annual frequency (monthly = 12 times per
        year, etc).
        
        @params
        kwarg: source {str, [str]} - Name or list of names of desired item(s) to
            sum from every itemized job. E.g. ['tips', 'taxes']
        kwarg: period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period == 0:
          return total
        # Add all the money going out for all jobs
        for job in self.elements:
          total += job.total_out(period=period, source=source)
        return total
    
    def net_amount(self, period=1, source=None):
        """
        Return amount totals of all money for a specific source or sources
        calculated using the desired annual frequency (monthly = 12 times per
        year, etc).
        
        @params
        kwarg: source {str, [str]} - Name or list of names of desired item(s) to
            sum from every itemized job. E.g. ['tips', 'taxes']
        kwarg: period {str | num}  Default is 1. Some demoninator of a
            year for compatibility with PeriodicFinancialList class. E.g, to
            express hours/week, use 52.
        """
        self._trigger_gather()
        total = Decimal(0)
        if period == 0:
            return total
        # Combine all the net amounts in all the jobs from particular sources
        for job in self.elements:
          total += job.net_amount(period=period, source=source)
        return total
    
    def to_json(self):
        """Creates line item list suitable for Legal Server API."""
        return [job.to_json() for job in self.elements]


class ALAsset(ALIncome):
    """Like income but the `value` attribute is optional."""
    def amount(self, period=1):
      if not hasattr(self, 'value'):
        return 0
      else:
        return super(ALAsset, self).amount(period=period)


class ALAssetList(ALIncomeList):
    def init(self, *pargs, **kwargs):
      super().init(*pargs, **kwargs)  
      self.object_type = ALAsset
    
    def market_value(self, source=None):
        """Returns the total market value of values in the list."""
        result = Decimal(0)
        for item in self.elements:
            if source is None:
                result += Decimal(item.market_value)
            elif isinstance(source, list): 
                if item.source in source:
                    result += Decimal(item.market_value)
            else:
                if item.source == source:
                    result += Decimal(item.market_value)
        return result
    
    # Q: Does this need to work per period?
    def balance(self, source=None):
        self._trigger_gather()
        result = Decimal(0)
        for item in self.elements:
            if source is None:
                result += Decimal(item.balance)
            elif isinstance(source, list): 
                if item.source in source:
                    result += Decimal(item.balance)
            else:
                if item.source == source:
                    result += Decimal(item.balance)
        return result
    
    def owners(self, source=None):
        """
        Returns a set of the unique owners for the specified source of asset
        stored in the list. If source is None, returns all unique owners in the
        ALAssetList.
        """
        owners=set()
        if source is None:
            for item in self.elements:
                if hasattr(item, 'owner'):
                    owners.add(item.owner)
        elif isinstance(source, list):
            for item in self.elements:
                if hasattr(item, 'owner') and hasattr(item, 'source') and item.source in source:
                    owners.add(item.owner)
        else:
            for item in self.elements:
                if hasattr(item,'owner') and item.source == source:
                    owners.add(item.owner)
        return owners


class ALVehicle(ALAsset):
    """Extends ALAsset. Vehicles have a .year_make_model() method."""
    def year_make_model(self):
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
    it's designed to store in a list, not a dictionary.
    """
    # Q: "it's designed to store" means "because ALSimpleValue is a list instead
    # of a dictionary? Or because ALSimpleValueList is? Maybe "to be stored"?
    # Q: add a `.delta()` that just returns positive or negative 1 depending on item?
    
    # Q: da `period` is not necessarily a yearly values while ours are yearly values, so maybe we can take the opportunity to come up with a more appropriate way to refer to ours
    # Q: da `amount` is not based on a yearly period, but an undetermined period, so maybe this is a similar opportunity to use our own name.
    def amount(self):
        """
        If desired, to use as a ledger, values can be signed. Setting
        transaction_type = 'expense' makes the value negative. Use min=0 in that
        case.
        """
        # Q: Why does `ALSimpleValue.amount()` not use Decimal?
        if hasattr(self, 'transaction_type'):
            return (self.value * -1) if (self.transaction_type == 'expense') else self.value
        else:
            return self.value

    def __str__(self):
        return str(self.amount())


class ALValueList(DAList):
    """Represents a filterable DAList of ALSimpleValues."""
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALSimpleValue        

    def sources(self):
        """
        Returns a set of the unique sources of values stored in the list. Will
        fail if any items in the list leave the source field unspecified.
        """
        sources = set()
        for item in self.elements:
            if hasattr(item, 'source'):
                sources.add(item.source)
        return sources
        
    def total(self, source=None):
        """
        Returns the total value in the list, gathering the list items if
        necessary. You can specify source, which may be a list, to coalesce
        multiple entries of the same source.
        """
        self._trigger_gather()
        result = Decimal(0)
        if source is None:
            for item in self.elements:
                result += Decimal(item.amount())
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.amount())
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.amount())
        return result


class ALLedger(ALValueList):
    """
    Represents an account ledger. Adds calculate method which adds a running
    total to the ledger.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)              

    def calculate(self):
        """
        Sort the ledger by date, then add a running total to each ledger entry.
        """
        self.elements.sort(key=lambda y: y.date)
        running_total = 0
        for entry in self.elements:
            running_total += entry.amount()
            entry.running_total = running_total
