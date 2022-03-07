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


class ALSimpleValue(DAObject):
    """
    Like a Value object, but no fiddling around with .exists attribute
    because it's designed to store in a list, not a dictionary.
    """
    # Q: "it's designed to store" means "because this is a dictionary instead
    # of a list?
    # Q: add a `.delta()` that just returns positive or negative 1 depending on item?
    
    def amount(self):
        """
        If desired, to use as a ledger, values can be signed. Setting
        transaction_type = 'expense' makes the value negative. Use min=0
        in that case.
        """
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
        result = 0
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
    def owners(self, source=None):
        """
        Returns a set of the unique owners for the specified source of
        income stored in the list. If source is None, returns all unique
        owners in the ALIncomeList.
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

    def total(self, times_per_year=1, source=None, owner=None):
        """
        Returns the total periodic value in the list, gathering the list
        items if necessary. You can specify a `source`, which may be a list,
        to only add entries of the matching source. If you specify the
        `source` you can also specify one `owner`.
        """
        # Q: can `owner` be a list? I see that `.owners()` returns a set
        self._trigger_gather()
        result = 0
        if times_per_year == 0:
            return(result)
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
    
    def market_value(self, source=None):
        """Returns the total market value of values in the list."""
        result = 0
        for item in self.elements:
            if source is None:
                # Q: I don't see where ALIncome has a .market_value
                result += Decimal(item.market_value)
            elif isinstance(source, list): 
                if item.source in source:
                    result += Decimal(item.market_value)
            else:
                if item.source == source:
                    result += Decimal(item.market_value)
        return result
    
    # Q: What is balance vs. total vs. market value?
    def balance(self, source=None):
        self._trigger_gather()
        result = 0
        for item in self.elements:
            if source is None:
                # Q: I don't see where ALIncome has a .balance
                result += Decimal(item.balance)
            elif isinstance(source, list): 
                if item.source in source:
                    result += Decimal(item.balance)
            else:
                if item.source == source:
                    result += Decimal(item.balance)
        return result
    
    def to_json(self):
        """Creates income list suitable for Legal Server API."""
        return json.dumps([{
          "source": income.source,
          "frequency": float(income.period),
          "amount": income.value
        } for income in self.elements])


class ALJob(ALIncome):
    """
    Represents a job that may be hourly or pay-period based. If
    non-hourly, may specify gross and net income amounts. This is a
    more common way of reporting income.
    """
    def gross_for_period(self, times_per_year=1):
        """Gross amount is identical to value."""
        return self.amount(times_per_year = times_per_year)
    
    # Q: Not sure of the name, but something like `net_value` or
    # `net_amount` seems indistinguishable from `.net`. Maybe
    # there should be `payment` and `deductions` and `.net()`
    # like ALPaystub
    def net_for_period(self, times_per_year=1):
        """
        Returns the net amount provided by the user
        (e.g. gross minus deductions) for the time period given.
        Only applies if value is non-hourly.
        """
        return (Decimal(self.net) * Decimal(self.period)) / Decimal(times_per_year)
    
    def name_address_phone(self):
        """Returns name, address and phone number of employer."""
        return self.employer + ': ' + self.employer_address + ', ' + self.employer_phone
    
    def normalized_hours(self, times_per_year):
        """Returns the number of hours worked in a given period."""
        return (float(self.hours_per_period) * int(self.period)) / int(times_per_year)


class ALJobList(ALIncomeList):
    """
    Represents a list of jobs. Adds the `.net_for_period()` and
    `.gross_for_period()` methods to the ALIncomeList class. It's a
    more common way of reporting income.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALJob
    
    def gross_for_period(self, times_per_year=1, source=None):
        self._trigger_gather()
        result = 0
        if times_per_year == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.gross_for_period(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.gross_for_period(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.gross_for_period(times_per_year=times_per_year))
        return result
    
    def net_for_period(self, times_per_year=1, source=None):
        self._trigger_gather()
        result = 0
        if times_per_year == 0:
            return(result)
        if source is None:
            for item in self.elements:
                result += Decimal(item.net_for_period(times_per_year=times_per_year))
        elif isinstance(source, list):
            for item in self.elements:
                if item.source in source:
                    result += Decimal(item.net_for_period(times_per_year=times_per_year))
        else:
            for item in self.elements:
                if item.source == source:
                    result += Decimal(item.net_for_period(times_per_year=times_per_year))
        return result


# Q: Does `paystub.is_hourly` make sense? (not really)
# Q: Does this really need to be an ALIncomeList
class ALPaystub(DAList):
    """
    Represents a job that can have multiple sources of earned income
    and deductions. It may be hourly or pay-period based. If non-hourly,
    it may specify gross and net income amounts. The amounts gotten can
    be filtered by the source of the income. This is a less common way
    of reporting income.
    
    The `.elements` attribute of this object are plain `PeriodicValue`s.
    
    There is one period per job for tips, wages, deductions, etc.
    
    Every line item's `.transaction_type` must be defined to get net and gross
    for a job.
    
    WARNING: Each source can only have one line item associated with it.
    
    attribs:
    .is_hourly {Bool}
    .hourly_rate {float}
    .hours_per_period {int}
    .period {float}
    .employer {Individual}
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.elements = list()
        self.object_type = PeriodicValue
        if not hasattr(self, 'employer'):
          self.initializeAttribute('employer', Individual)
    
    def sources(self):
        """Returns a set of the unique sources of the elements."""
        sources = set()
        for item in self.elements:
            if hasattr(item, 'source'):
                sources.add(item.source)
        return sources
    
    # Q: Should `source` be `id`? That only makes sense for jobs, not
    # incomes/assets, so they then won't share an interface.
    # Maybe `name`? Or do we need categories, not `id`s? In what
    # situations would there be income values from the same "type"/`source`?
    # Names for transaction_type: in_or_out? delta?
    # Q: allow filtering by `owners`?
    def line_items(self, source=None, transaction_type=None):
      """
      Returns the list of line items filtered by source (e.g. 'tip')
      or list of sources (e.g. [ 'tip', 'commission', 'deduction' ])
      or by transaction_type or both.
      
      If no filters are specified, returns all line items.
      
      Options for the `source` value come from the source names you create.
      Options for the `transaction_type` value are 'payment' or 'deduction'.
      # Q: Do they have to be limited to that?
      """
      self._trigger_gather()
      all_items = self.elements
      
      # If no filters, return all items
      if source is None and transaction_type is None:
        return all_items
      
      # Filter by sources
      if source is None:
        # By default, use all items. Don't mutate the original list.
        source_items = all_items[:]
      else:
        # Ensure we're using a list no matter what
        if isinstance(source, list): sources = source
        else: sources = [source]
        # Put all matching items in a list
        source_items = [item for item in all_items if item.source in sources]
        
      # Filter by transaction_type
      if transaction_type is None:
        filtered_items = source_items
      else:
        # Ensure we're using a list no matter what
        filtered_items = [item for item in source_items if item.transaction_type == transaction_type]
      
      return filtered_items
    
    # Q: Should `times_per_year` default be the period of the paystub?
    # (instead of 1)
    # Q: Should `times_per_year` be a string that's the "name" of the period?
    # Calling it just `period` is a bit confusing when the value is a number.
    # e.g. `period = 12`, to me, doesn't shout out "monthly".
    def absolute_period_value(self, line_item, times_per_year=1):
        """
        Returns the amount earned or deducted over the specified period for
        the specified line item of the job.
        """
        if times_per_year == 0:
          return Decimal(0)
        # Use the appropriate cacluation
        if hasattr(self, 'is_hourly') and self.is_hourly:
          return (Decimal(line_item.value) * Decimal(self.hours_per_period) * Decimal(self.period)) / Decimal(times_per_year)
        else:
          return (Decimal(line_item.value) * Decimal(self.period)) / Decimal(times_per_year)
    
    # Q: Allow `line_item` to be a string (source/id name)?
    # Names: line_item_period_value? item_period_value?
    def period_value(self, line_item, times_per_year=1):
      """
      Returns the amount earned or deducted over the specified period for
      the given line item as a positive or negative value.
      
      Example:
      # Get the montly value of the job's tips
      my_multipart_job.period_value( 'tips', times_per_year=12 )
      # 424.44
      # Get the yearly value of the job's deductions
      my_multipart_job.period_value( 'deductions', times_per_year=1 )
      # -202.65
      """
      absolute_value = self.absolute_period_value( line_item, times_per_year=times_per_year )
      if line_item.transaction_type == 'deduction' or line_item.transaction_type == 'out':
        return Decimal(-1) * absolute_value
      else:
        return absolute_value
    
    # Q: Also filter by `owners`?
    def gross(self, source=None, times_per_year=1):
        """
        Returns the sum of positive values (payments) for a given pay
        period. Can be filtered by one line item source or a list of sources.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Filter result by source if desired
        line_items = self.line_items( source=source )
        # Add up positive values
        for line_item in line_items:
          if line_item.transaction_type != 'deduction':
            total += self.period_value( line_item, times_per_year=times_per_year )
        return total
    
    # Q: Also filter by `owners`?
    def net(self, times_per_year=1, source=None):
        """
        Returns the net (payments minus deductions) value of the job
        for a given pay period. Can be filtered by a line item source
        or a list of sources.
        """
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Filter result by source if desired
        line_items = self.line_items( source=source )
        # Add up positive and negative values
        for line_item in line_items:
          total += self.period_value( line_item, times_per_year=times_per_year )
        return total
    
    def total(self, times_per_year=1, source=None):
      return self.net(times_per_year=times_per_year, source=source)
    
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
        return round((float(self.hours_per_period) * float(self.period)) / int(times_per_year))
    
    def to_json(self):
        """Creates line item list suitable for Legal Server API."""
        return json.dumps([{
          "source": item.source,
          "frequency": float(self.period),
          # Should this be called just `value`? Does Legal Server API
          # call it `amount`?
          "amount": float( self.period_value(item, times_per_year=self.period ))
        } for item in self.elements])


class ALPaystubList(DAList):
    """
    Represents a list of jobs that can have both payments and deductions.
    This is a less common way of reporting income.
    """
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)     
        self.object_type = ALPaystub
    
    def sources(self):
        """Returns a set of the unique sources of the elements."""
        sources = set()
        for item in self.elements:
            if hasattr(item, 'source'):
                sources.add(item.source)
        return sources
    
    def gross(self, times_per_year=1, source=None):
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list.
        if source is None:
          sources = self.sources()
        elif isinstance(source, list):
          sources = source
        else:
          sources = [source]
        # Filter by source.
        filtered = [stub for stub in self.elements if stub.source in sources]
        # Add filtered grosses together
        for stub in filtered:
          total += stub.gross(times_per_year=times_per_year)
        return total
    
    def net(self, times_per_year=1, source=None):
        self._trigger_gather()
        total = Decimal(0)
        if times_per_year == 0:
            return total
        # Make sure we're always working with a list.
        if source is None:
          sources = self.sources()
        elif isinstance(source, list):
          sources = source
        else:
          sources = [source]
        # Filter by source.
        filtered = [stub for stub in self.elements if stub.source in sources]
        # Add filtered nets together
        for stub in filtered:
          total += stub.net(times_per_year=times_per_year)
        return total
    
    def total(self, times_per_year=1, source=None):
      return self.net(times_per_year=times_per_year, source=source)
    
    def to_json(self):
        """Creates line item list suitable for Legal Server API."""
        return json.dumps([{
          "source": stub.source,
          "frequency": float(stub.period),
          "gross": float(stub.gross(times_per_year=stub.period)),
          "net": float(stub.net(times_per_year=stub.period)),
          "line_items": stub.to_json()
        } for stub in self.elements])


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


class ALVehicle(ALSimpleValue):
    """Vehicles have a method year_make_model()."""
    def year_make_model(self):
        return self.year + ' / ' + self.make + ' / ' + self.model


class ALVehicleList(ALValueList):
    """List of vehicles, extends ALValueList. Vehicles have a method year_make_model()."""
    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = ALVehicle


class ALAsset(ALIncome):
  """Like income but with the `value` attribute is optional."""
  def amount(self, times_per_year=1):
    if not hasattr(self, 'value'):
      return 0
    else:
      return super(ALAsset, self).amount(times_per_year=times_per_year)


class ALAssetList(ALIncomeList):
      def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)  
        self.object_type = ALAsset
