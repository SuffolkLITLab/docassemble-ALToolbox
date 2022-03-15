# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import DAObject, DAList, DAOrderedDict, PeriodicValue, DAEmpty, Individual, comma_list, log
from decimal import Decimal
import datetime
import docassemble.base.functions
import json


def flatten(listname,index=1):
    """
    Return just the nth item in an 2D list. Intended to use for multiple
    choice option lists in Docassemble. e.g., flatten(asset_source_list())
    will return ['Savings','Certificate of Deposit'...].
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
    """ Returns text describing the number of intervals of the period in a year."""
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
    Defaults to most recent 15 years+1. Useful to populate a combobox of
    years where the most recent ones are most likely. E.g. automobile years
    or birthdate. Keyword paramaters: years, order (descending or ascending),
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
    Represents an income which may have an hourly rate or a salary.
    Hourly rate incomes must include hours and period. 
    Period is some demoninator of a year for compatibility with
    PeriodicFinancialList class. E.g, to express hours/week, use 52.
    """
    # Q: It's actually the value per period. "amount" isn't super clear. Change name?
    # Name: times_per_year was period. maybe period_frequency? value_frequency?
    def amount(self, times_per_year=1):
        """Returns the income over the specified period."""
        ## Q: Conform to behavior of docassemble PeriodicValue?
        #if not hasattr(self, 'value'):
        #  return Decimal(0)
        if hasattr(self, 'is_hourly') and self.is_hourly:
            return Decimal(self.hourly_rate * self.hours_per_period * self.period) / Decimal(times_per_year)
        else:
          return (Decimal(self.value) * Decimal(self.period)) / Decimal(times_per_year)


class ALIncomeList(DAList):
    """
    Represents a filterable DAList of income items, each of which has
    an associated period or hourly wages.
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

    # Q: Instead require `source` to always be a list? They just have
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
    def total(self, times_per_year=1, source=None, owner=None):
        """
        Returns the total periodic value in the list, gathering the list
        items if necessary. You can specify a `source`, which may be a list,
        to only add entries of the matching source. If you specify the
        `source` you can also specify one `owner`.
        """
        # Q: can `owner` be a list? I see that `.owners()` returns a set
        self._trigger_gather()
        result = Decimal(0)
        if times_per_year == 0:
            return result
        if source is None:
            # Q: Should this allow the user to filter _just_ by the `owner`
            # as well if they include just the `owner`?
            for item in self.elements:
                result += Decimal(item.amount(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    if owner is None: # if we don't care who the owner is
                        result += Decimal(item.amount(times_per_year=times_per_year))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if item.source == source:
                    if owner is None:
                        result += Decimal(item.amount(times_per_year=times_per_year))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(times_per_year=times_per_year))
        return result
    
    def to_json(self):
        """Returns an income list suitable for Legal Server API."""
        return json.dumps([{
          "source": income.source,
          "frequency": float(income.period),
          # Q: shouldn't this use `amount()`? [what does this second question mean? ->] Is this why times_per_year needs to default to 1?
          # Q: Actually, in docassemble, `.amount()` always defaults to a period of 1, so if this is `amount`, it would use a year as a period, so maybe this really should be called `value` instead.
          "value": income.value
        } for income in self.elements])


class ALJob(ALIncome):
    """
    Represents a job that may be hourly or pay-period based. If
    non-hourly, may specify gross and net income amounts. This is a
    more common way of reporting income as opposed to ALItemizedJob.
    """
    def gross_amount(self, times_per_year=1):
        """Gross amount is identical to ALIncome amount."""
        return self.amount(times_per_year = times_per_year)
    
    # Q: Not sure of the name, but something like `net_value` or
    # `net_amount` seems indistinguishable from `.net`. Maybe
    # there should be `payment` and `deductions` and `.net()`
    # like ALItemizedJob
    def net_amount(self, times_per_year=1):
        """
        Returns the net amount provided by the user
        (e.g. gross minus deductions) for the time period given.
        Only applies if value is non-hourly.
        """
        return (Decimal(self.net) * Decimal(self.period)) / Decimal(times_per_year)
    
    def employer_name_address_phone(self):
        """Returns name, address and phone number of employer."""
        return self.employer + ': ' + self.employer_address + ', ' + self.employer_phone
    
    def normalized_hours(self, times_per_year):
        """Returns the number of hours worked in a given period."""
        return (float(self.hours_per_period) * int(self.period)) / int(times_per_year)


class ALJobList(ALIncomeList):
    """
    Represents a list of jobs. Adds the `.net_amount()` and
    `.gross_amount()` methods to the ALIncomeList class. It's a
    more common way of reporting income as opposed to ALItemizedJobList.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALJob
    
    def gross_amount(self, times_per_year=1, source=None):
        self._trigger_gather()
        result = 0
        if times_per_year == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.gross_amount(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.gross_amount(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.gross_amount(times_per_year=times_per_year))
        return result
    
    def net_amount(self, times_per_year=1, source=None):
        self._trigger_gather()
        result = 0
        if times_per_year == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.net_amount(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.net_amount(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.net_amount(times_per_year=times_per_year))
        return result

#def ValueForFrequency():
#  def __init__(self, *pargs, **kwargs):
#      super().init(*pargs, **kwargs)
#      self.is_hourly = kwargs.is_hourly
#      self.period = kwargs.period
#      self.hours_per_period = kwargs.hours_per_period
#      self.value = kwargs.value
#  
#  def for_frequency(self, times_per_year=1):
#      """
#      Returns the amount earned or deducted over the specified period for
#      the specified line item of the job.
#      """
#      if times_per_year == 0:
#        return Decimal(0)
#      # Use the appropriate cacluation
#      # Q: not deducted per hour, though.
#      if hasattr(self, 'is_hourly') and self.is_hourly:
#        return (Decimal(self.value) * Decimal(self.hours_per_period) * Decimal(self.period)) / Decimal(times_per_year)
#      else:
#        return (Decimal(self.value) * Decimal(self.period)) / Decimal(times_per_year)


class ALItemizedJob(DAObject):
    """
    Notes:
    # ~Add assets, add jobs, all in same way?~ they have different stuff
    # ~ALIncomeList should be able to use ALItemizedJob in the same way that it uses all its other members?~ see below about `in` and `out`
    # What do we need to share?
    # ALItemizedJob {DAObject, DADict}
    # .in/incomes/payments {DAList? ALIncomeList? DADict? depending on development}
    # .out/deductions {DAList? ALIncomeList? DADict depending on development}
    # Look at needs in SSI interview (https://github.com/nonprofittechy/docassemble-ssioverpaymentwaiver)
    # .sources will have to take into account the two lists
    # `amount` is in docassemble
    # How do I allow this to be in an ALIncomeList if interview developers
    # are going to say ALIncomeList.market_value() - these items will error
    # when they are looped through. ALItemizedJobList will as well.
    
    # in: commission, bonus, hourly wage (wages?), non-hourly wages (salary?), overtime, tips
    # out: deductions, garnishments, dues, insurance

    # https://fingercheck.com/the-difference-between-a-paycheck-and-a-pay-stub/
    #Deductions are the amounts subtracted or withheld from the total pay, including the income tax percentage of an employee’s gross wages.
    #Social security and Medicare are deducted based on the income over the set threshold.
    #Other deductions can include state and local income taxes, employee 401K contributions, insurance payments, profit sharing, union dues, garnishments and unemployment insurance etc.
    job_income_choices = [
    ('tips', 'Tips'),
    ('deductions', 'Deductions'),
    ('garnishments', 'Garnishments')
    """
    """
    Requirements:
    - A job can be hourly
    - Despite an hourly job, some individual items must be calcuated
      using the whole period
    - Some items will have their own periods
    - Devs need to be able to have different types of job base_pay (e.g.
      full time, part time) that they must be able to access separately
    - Users must be able to add arbitrary in/out items for a job
    - Devs may need to total amounts same names across different jobs (e.g.
      tips for all jobs, etc.)
    New:
    - need total in/income and total out/deductions
    - get jobs by attributes, total by job attribute
        da filter by attribute (raises exception)
        list comprehension
    12:03 Q describes something about attributes or methods or something (end time: 12:57)
    so an hour before the end, aprox
    """
    """
    Represents a job that can have multiple sources of earned income
    and deductions. It may be hourly or pay-period based. This is a less
    common way of reporting income than a plain ALJob.
    
    There is one period per itemized job.
    Caroline: Except maybe not. For deductions, etc.
    
    attribs:
    .is_hourly {bool}
    .hours_per_period {int}
    .period {str}
    .employer {Individual}
    .in_values {DADict}
    .out_values {DADict}
    """
    def init(self, *pargs, **kwargs):
      super().init(*pargs, **kwargs)
      if not hasattr(self, 'employer'):
        self.initializeAttribute('employer', Individual)
      # Q: Use complete_attribute = "value" for in/out items?
      # Money coming in
      if not hasattr(self, 'in_values'):
        self.initializeAttribute('in_values', DAOrderedDict.using(object_type=DAObject))
      # Money being taken out
      if not hasattr(self, 'out_values'):
        self.initializeAttribute('out_values', DAOrderedDict.using(object_type=DAObject))
    
    """
    interface:
    
    for_frequency, for_freq_per_year, per_year_frequency, value_for_times_per_year, value_for/per_annual_frequency/by_annual_frequency/by_yearly_frequency
    .net_per_frequency/net_for_frequency
    .gross_per_frequency/gross_for_frequency
    .line_items?
    .item_value_per_frequency/item_value_for_frequency
    
    ~No filtering necessary?~ Filtering for an item or multiple items is necessary
    """
    
    """
    getting "amount"s
    if not hasattr(line_item, 'value') or frequency == 0:
      return Decimal(0)
    
    if hasattr(line_item, 'period'):
      line_item.period
    else:
      self.period
    
    if hasattr(line_item, 'is_hourly'):
      is_hourly = line_item.is_hourly
    else:
      is_hourly = False
    """
    
    """
    Job has a period while asking for `amount` has a frequency?
    """
    
    """
    Interface
    job.money_in["wages"].value
    job.money_in["wages"].is_hourly = True
    job.money_in["commisions"].period = 12
    # divided_by = 52, annual_frequency=52
    all_jobs.total(["commissions", "bonuses"], frequency=52)
    if job.has_other and job.in_values.there_is_another and not job.others_gathered:
      job.get_other
      # OR
      job.others.gather()  # How to make this a different type of object?
      # OR
      job.money_in.other.gather()
      #job.money_out.other.gather()  # same structure for job.out_values?
      # OR
      # How would this work?
      job.money_in.gather()
      #job.money_out.gather()  # same structure for job.out_values?
      # OR?
      job.there_is_another = True
    else:
      job.there_is_another = False
      job.others_gathered = True
      job.gathered = True  # ??
    """
    
    def item_amount(self, item, annual_frequency=1):
      """
      Frequency default is annual (1)
      """
      if annual_frequency == 0:
        return Decimal(0)
      
      period = self.period
      if hasattr(item, 'period') and item.period:
        period = item.period
      
      is_hourly = False
      # Override if item should be calculated hourly (like wages)
      # Names: is_hourly -> calculate_hourly (for individual items)
      if self.is_hourly and hasattr(item, 'is_hourly'):
        is_hourly = item.is_hourly
      
      value = Decimal(0)
      if hasattr(item, 'value'):
        value = Decimal(item.value)
      
      # Use the appropriate cacluation
      if is_hourly:
        return (value * Decimal(self.hours_per_period) * Decimal(period)) / Decimal(annual_frequency)
      else:
        return (value * Decimal(period)) / Decimal(annual_frequency)  
    
    ## Is it worth getting multiple items? Should we just return one item?
    ## Do we return a dict instead? What is needed here?
    ## We need a way to add up values with certain names.
    #def get_items_named(self, names):
    #  """Returns a list of items with the name `name`, which can be a str or a list."""
    #  # Ensure we're using a list
    #  if not isinstance(names, list):
    #    names = [names]
    #  # Collect all those items
    #  all_items = []
    #  for name in names:
    #    if self.in_values.elements.get(name, None):
    #      all_items.append(self.in_values.get(name))
    #    else:
    #      # Return out value or None
    #      all_items.append(self.out_values.get(name, None))
    #  return all_items
    
    #def item_value_amount(self, item_value, times_per_year=1):
    #  """
    #  Frequency default is annual: `times_per_year=1`
    #  """
    #  # Q: change .period to .frequency or .times_per_year?
    #  if times_per_year == 0:
    #    return Decimal(0)
    #  frequency = self.period
    #  #if hasattr(item, 'period'):
    #  #  frequency = item.period
    #  #if hasattr(item, 'frequency'):
    #  #  frequency = item.frequency
    #  # Use the appropriate cacluation
    #  if hasattr(self, 'is_hourly') and self.is_hourly:
    #    #return (Decimal(value) * Decimal(self.hours_per_frequency) * Decimal(self.yearly_frequency)) / Decimal(times_per_year)
    #    return (Decimal(value) * Decimal(self.hours_per_period) * Decimal(frequency)) / Decimal(times_per_year)
    #  else:
    #    return (Decimal(value) * Decimal(frequency)) / Decimal(times_per_year)
    
    # Q: Would total in/out methods be useful?
    # Q: What aliases would be useful? We need gross and incomes, apparently. What else?
    # ---
    # In amount aliases
    # ---
    def total_in(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    def in_amount(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    def incomes(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    
    # ---
    # Out amount aliases
    # ---
    def out_amount(self, times_per_year=1, source=None):
      return self.total_out(times_per_year=times_per_year, source=source)
    def deductions(self, times_per_year=1, source=None):
      return self.total_out(times_per_year=times_per_year, source=source)
    
    # ---
    # Net aliases
    # ---
    # Names: `total_amount`?
    def total(self, times_per_year=1, source=None):
      return self.net_amount(times_per_year=times_per_year, source=source)
    def total_amount(self, times_per_year=1, source=None):
      return self.net_amount(times_per_year=times_per_year, source=source)
    
    # ---
    # Actual calculations
    # ---
    # Include filtering by name? So confused.
    def gross_amount(self, times_per_year=1, source=None):
      """
      Returns the sum of positive values (payments) for a given pay
      period (1 for yearly, 12 for monthly, etc). Default frequency value
      of 1 (yearly) so jobs can be normalized to each other easily (instead
      of using their own periods by default).
      """
      #self._trigger_gather()
      #self.in_values._trigger_gather()
      total = Decimal(0)
      if times_per_year == 0:
        return total
      # Make sure we're always working with a list of sources (names?)
      sources = self.to_source_list(source=source)
      # Add up all money coming in from a source
      for key, item in self.in_values.elements.items():
        if key in sources:
          total += self.item_amount(item, annual_frequency=times_per_year)
      return total
    
    def total_out(self, times_per_year=1, source=None):
      total = Decimal(0)
      if times_per_year == 0:
        return total
      # Make sure we're always working with a list of sources (names?)
      sources = self.to_source_list(source=source)
      # Add all the money going out
      for key, item in self.out_values.elements.items():
        if key in sources:
          total += self.item_amount(item, annual_frequency=times_per_year)
      return total
    
    def net_amount(self, times_per_year=1, source=None):
      """
      Returns the net (payments minus deductions) value of the job
      for a given pay period (1 for yearly, 12 for monthly, etc).
      Default frequency value of 1 so all jobs can be normalized.
      """
      #self._trigger_gather()
      #self.in_values._trigger_gather()
      #self.out_values._trigger_gather()
      total = Decimal(0)
      if times_per_year == 0:
        return total
      # Make sure we're always working with a list of sources (names?)
      sources = self.to_source_list(source=source)
      # Add up all money coming in
      for key, item in self.in_values.elements.items():
        if key in sources:
          total += self.item_amount(item, annual_frequency=times_per_year)
      # Subtract the money going out
      for key, item in self.out_values.elements.items():
        if key in sources:
          total -= self.item_amount(item, annual_frequency=times_per_year)
      return total
    
    def to_source_list(self, source=None):
      """
      Given a string or list of strings, return a list of strings. If no strings given,
      return a list of all keys in both the `in_values` and `out_values` DADicts.
      """
      # Make sure we're always working with a list of sources (names?)
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
    
    ## Q: Should `source` be `id`? That only makes sense for jobs, not
    ## incomes/assets, so they then won't share an interface.
    ## Maybe `name`? Or do we need categories, not `id`s? In what
    ## situations would there be income values from the same "type"/`source`?
    ## Names for transaction_type: in_or_out? delta?
    #def line_items(self, source=None, transaction_type=None):
    #  """
    #  Returns the list of line items filtered by source (e.g. 'tip')
    #  or list of sources (e.g. [ 'tip', 'commission', 'deduction' ])
    #  or by transaction_type or both.
    #  
    #  If no filters are specified, returns all line items.
    #  
    #  Options for the `source` value come from the source names you create.
    #  Options for the `transaction_type` value are 'payment' or 'deduction'.
    #  # Q: Do they have to be limited to that?
    #  """
    #  self._trigger_gather()
    #  all_items = self.elements
    #  
    #  # If no filters, return all items
    #  if source is None and transaction_type is None:
    #    return all_items
    #  
    #  # Filter by sources
    #  if source is None:
    #    # By default, use all items. Don't mutate the original list.
    #    source_items = all_items[:]
    #  else:
    #    # Ensure we're using a list no matter what
    #    if isinstance(source, list): sources = source
    #    else: sources = [source]
    #    # Put all matching items in a list
    #    source_items = [item for item in all_items if item.source in sources]
    #    
    #  # Filter by transaction_type
    #  if transaction_type is None:
    #    filtered_items = source_items
    #  else:
    #    # Ensure we're using a list no matter what
    #    filtered_items = [item for item in source_items if item.transaction_type == transaction_type]
    #  
    #  return filtered_items
    #  
    ## Q: Should `times_per_year` default be the period of the ItemizedJob?
    ## (instead of 1). Probably not so they're all normalized when there's no arg.
    ## Q: Should `times_per_year` be a string that's the "name" of the period?
    ## Calling it just `period` is a bit confusing when the value is a number.
    ## e.g. `period = 12`, to me, doesn't shout out "monthly".
    ## Q: Allow `line_item` to be a string (source/id name)?
    ## Names: line_item_period_value? item_period_value?
    
    def employer_name_address_phone(self):
        """
        Returns concatenation of employer name and, if they exist,
        employer address and phone number.
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
    
    def normalized_hours(self, times_per_year):
        """Returns the number of hours worked in a given period for an hourly job."""
        # Q: Is there a safe value to return if it's not hourly?
        return round((float(self.hours_per_period) * float(self.period)) / float(times_per_year))
    
    # to_json string? json.dumps returns str right? Don't we want to
    # let them prety print it their own way?
    def to_json(self):
      """Creates line item list suitable for Legal Server API."""
      return json.dumps({
        "name": self.name,
        "frequency": float(self.period),
        # Q: Should this be called just `value`? Does Legal Server API
        # call it `amount`?
        "value": float(self.net_amount(times_per_year=self.period)),
        "in_values": self.items_json(self.in_values),
        "out_values": self.items_json(self.out_values)
      })
    
    # Q: A python ordered dict won't translate to json, right?
    def items_json(self, item_dict):
      """
      Given a dict of ALItemizedJob "in" or "out" objects, return
      a string of JSON for that dict.
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
    Represents a list of jobs that can have both payments and deductions.
    This is a less common way of reporting income.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALItemizedJob
    
    #def gross_amount_for(self, source, times_per_year=1):
    #  self._trigger_gather()
    #  total = Decimal(0)
    #  if times_per_year == 0:
    #      return total
    #  # Make sure we're always working with a list.
    #  if source is None:
    #    sources = self.sources()
    #  elif isinstance(source, list):
    #    sources = source
    #  else:
    #    sources = [source]
    #  for one_source in sources
    #  pass
    
    #def filter_items_by(self, source=None):
    #  """
    #  Return the items matching the filter. Currently can only filter by `source`.
    #  
    #  @params
    #  `source` {str, [str]} - String or list of strings of the names of itemized
    #      job items. E.g. ['tips', 'taxes']
    #  """
    #  self._trigger_gather()
    #  all_items = []
    #  # If not filtering by anything
    #  if source is None:
    #    for job in self.elements:
    #      for in_item in job.in_values.elements:
    #        all_items.
    #  return 
    
    # Q: Do we want some way to have a running total?
    # ---
    # In amount aliases
    # ---
    def total_in(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    def in_amount(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    def incomes(self, times_per_year=1, source=None):
      return self.gross_amount(times_per_year=times_per_year, source=source)
    
    # ---
    # Out amount aliases
    # ---
    def out_amount(self, times_per_year=1, source=None):
      return self.total_out(times_per_year=times_per_year, source=source)
    def deductions(self, times_per_year=1, source=None):
      return self.total_out(times_per_year=times_per_year, source=source)
    
    # ---
    # Net aliases
    # ---
    def total(self, times_per_year=1, source=None):
      return self.net_amount(times_per_year=times_per_year, source=source)
    def total_amount(self, times_per_year=1, source=None):
      return self.net_amount(times_per_year=times_per_year, source=source)
    
    # ---
    # Actual calculations
    # ---
    def gross_amount(self, times_per_year=1, source=None):
      """
      Return amount totals of money coming in for a specific source or sources,
      calculated using the desired annual frequency (monthly = 12 times per year, etc).
      
      @params
      kwarg: source {str, [str]} - String or list of strings of the names of itemized
          job items. E.g. ['tips', 'taxes']
      kwarg: times_per_year {int} - Default is `1`. The desired frequency of the value.
          E.g. 12 to get the value per month, 52 for per week. This is want makes
          an `amount` different than a `value`
      """
      self._trigger_gather()
      total = Decimal(0)
      if times_per_year == 0:
          return total
      # Add all job gross amounts from particular sources
      for job in self.elements:
        total += job.gross_amount(times_per_year=times_per_year, source=source)
      return total
    
    def total_out(self, times_per_year=1, source=None):
      """
      Return amount totals of money going out for a specific source or sources,
      calculated using the desired annual frequency (monthly = 12 times per year, etc).
      
      @params
      kwarg: source {str, [str]} - String or list of strings of the names of itemized
          job items. E.g. ['tips', 'taxes']
      kwarg: times_per_year {int} - Default is `1`. The desired frequency of the value.
          E.g. 12 to get the value per month, 52 for per week. This is want makes
          an `amount` different than a `value`
      """
      self._trigger_gather()
      total = Decimal(0)
      if times_per_year == 0:
        return total
      # Add all the money going out for all jobs
      for job in self.elements:
        total += job.total_out(times_per_year=times_per_year, source=source)
      return total
    
    def net_amount(self, times_per_year=1, source=None):
      """
      Return amount totals of all money for a specific source or sources,
      calculated using the desired annual frequency (monthly = 12 times per year, etc).
      
      @params
      kwarg: source {str, [str]} - String or list of strings of the names of itemized
          job items. E.g. ['tips', 'taxes']
      kwarg: times_per_year {int} - Default is `1`. The desired frequency of the value.
          E.g. 12 to get the value per month, 52 for per week. This is want makes
          an `amount` different than a `value`
      """
      self._trigger_gather()
      total = Decimal(0)
      if times_per_year == 0:
          return total
      # Total all the totals in all the jobs from particular sources
      for job in self.elements:
        total += job.net_amount(times_per_year=times_per_year, source=source)
      return total
    
    #def sources(self):
    #    """Returns a set of the unique sources of the elements."""
    #    sources = set()
    #    for item in self.elements:
    #        if hasattr(item, 'source'):
    #            sources.add(item.source)
    #    return sources
    #
    #def gross_old(self, times_per_year=1, source=None):
    #    self._trigger_gather()
    #    total = Decimal(0)
    #    if times_per_year == 0:
    #        return total
    #    # Make sure we're always working with a list.
    #    if source is None:
    #      sources = self.sources()
    #    elif isinstance(source, list):
    #      sources = source
    #    else:
    #      sources = [source]
    #    # Filter by source.
    #    filtered = [stub for stub in self.elements if stub.source in sources]
    #    # Add filtered grosses together
    #    for stub in filtered:
    #      total += stub.gross_amount(times_per_year=times_per_year)
    #    return total
    #
    #def net_old(self, times_per_year=1, source=None):
    #    self._trigger_gather()
    #    total = Decimal(0)
    #    if times_per_year == 0:
    #        return total
    #    # Make sure we're always working with a list.
    #    if source is None:
    #      sources = self.sources()
    #    elif isinstance(source, list):
    #      sources = source
    #    else:
    #      sources = [source]
    #    # Filter by source.
    #    filtered = [stub for stub in self.elements if stub.source in sources]
    #    # Add filtered nets together
    #    for stub in filtered:
    #      total += stub.net_amount(times_per_year=times_per_year)
    #    return total
    #
    #def total(self, times_per_year=1, source=None):
    #  return self.net_old(times_per_year=times_per_year, source=source)
    
    def to_json(self):
        """Creates line item list suitable for Legal Server API."""
        return json.dumps([{
          "source": stub.source,
          "frequency": float(stub.period),
          "gross": float(stub.gross(times_per_year=stub.period)),
          "net": float(stub.net(times_per_year=stub.period)),
          "items": stub.to_json()
        } for stub in self.elements])


class ALAsset(ALIncome):
  """Like income but the `value` attribute is optional."""
  def amount(self, times_per_year=1):
    if not hasattr(self, 'value'):
      return 0
    else:
      return super(ALAsset, self).amount(times_per_year=times_per_year)


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
        Returns a set of the unique owners for the specified source of
        asset stored in the list. If source is None, returns all unique
        owners in the ALAssetList.
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
    List of vehicles. Extends ALAssetList. Vehicles have
    a .year_make_model() method.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALVehicle


class ALSimpleValue(DAObject):
    """
    Like a Value object, but no fiddling around with .exists attribute
    because it's designed to store in a list, not a dictionary.
    """
    # Q: "it's designed to store" means "because ALSimpleValue is a list instead
    # of a dictionary? Or because ALSimpleValueList is? Maybe "to be stored"?
    # Q: add a `.delta()` that just returns positive or negative 1 depending on item?
    
    # Q: da `period` is not necessarily a yearly values while ours are yearly values, so maybe we can take the opportunity to come up with a more appropriate way to refer to ours
    # Q: da `amount` is not based on a yearly period, but an undetermined period, so maybe this is a similar opportunity to use our own name.
    def amount(self):
        """
        If desired, to use as a ledger, values can be signed. Setting
        transaction_type = 'expense' makes the value negative. Use min=0
        in that case.
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
        Returns a set of the unique sources of values stored in the list.
        Will fail if any items in the list leave the source field unspecified.
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
    Represents an account ledger. Adds calculate method which adds
    a running total to the ledger.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)              

    def calculate(self):
        """Sort the ledger by date, then add a running total to each ledger entry."""
        self.elements.sort(key=lambda y: y.date)
        running_total = 0
        for entry in self.elements:
            running_total += entry.amount()
            entry.running_total = running_total
