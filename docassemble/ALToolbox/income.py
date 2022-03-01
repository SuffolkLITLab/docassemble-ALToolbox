# Based on https://github.com/GBLS/docassemble-income/blob/master/docassemble/income/income.py

from docassemble.base.util import DAObject, DAList, DADict, DAOrderedDict, Value, PeriodicValue, FinancialList, PeriodicFinancialList, DAEmpty
from decimal import Decimal
import datetime
import docassemble.base.functions
from collections import OrderedDict
import json


def flatten(listname,index=1):
    """Return just the nth item in an 2D list. Intended to use for multiple choice option lists in Docassemble.
        e.g., flatten(asset_type_list()) will return ['Savings','Certificate of Deposit'...] """
    return [item[index] for item in listname]

def income_period_list():
    return [
        [12,"Monthly"],
        [1,"Yearly"],
        [52,"Weekly"],
        [24,"Twice per month"],
        [26,"Once every two weeks"],
        [4,"Once every 3 months"]  # quarterly
    ]

def income_period(index):
    # income_period_description
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
    """Returns a list of the most recent years, continuing into the future. Defaults to most recent 15 years+1. Useful to populate
        a combobox of years where the most recent ones are most likely. E.g. automobile years or birthdate.
        Keyword paramaters: years, order (descending or ascending), future (defaults to 1)"""
    now = datetime.datetime.now()
    if order=='ascending':
        return list(range(now.year-years,now.year+future,1))
    else:
        return list(range(now.year+future,now.year-years,-1))

def asset_type_list() :
    """Returns a list of assset types for a multiple choice dropdown"""
    type_list =  DAOrderedDict()
    type_list.auto_gather = False
    type_list.gathered = True
    type_list.elements.update([
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
    return type_list

def income_type_list() :
    """Returns a dict of income types for a multiple choice dropdown"""
    type_list = DAOrderedDict()
    type_list['wages'] = 'A job or self-employment'

    type_list.elements.update(non_wage_income_list())
    type_list.auto_gather = False
    type_list.gathered = True

    return type_list

def non_wage_income_list():
    """Returns a dict of income types, excluding wages"""
    type_list = DAOrderedDict()
    type_list.auto_gather = False
    type_list.gathered = True
    type_list.elements.update([
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
    return type_list

def expense_type_list() :
    """Returns a dict of expense types for a multiple choice dropdown"""
    type_list = DAOrderedDict()
    type_list.auto_gather = False
    type_list.gathered = True
    type_list.elements.update([
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
    return type_list


class ALIncome(PeriodicValue):
    """Represents an income which may have an hourly rate or a salary.
        Hourly rate incomes must include hours and period. 
        Period is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express hours/week, use 52 """

    def amount(self, period_to_use=1):
        # period_to_return?
        """Returns the amount earned over the specified period """
        if hasattr(self, 'is_hourly') and self.is_hourly:
            return Decimal(self.hourly_rate * self.hours_per_period * self.period) / Decimal(period_to_use)        
        return (Decimal(self.value) * Decimal(self.period)) / Decimal(period_to_use)


class ALDeduction(PeriodicValue):
    """Returns a negative value that represents a income deduction.
        Can those have an hourly rate or a salary?
        Hourly rate deductions must include hours and period. 
        Period is some demoninator of a year for compatibility with
        PeriodicFinancialList class. E.g, to express hours/week, use 52"""
    
    def amount(self, interval_per_year_to_return=1):
        """Returns the amount earned over the specified period"""
        if hasattr(self, 'is_hourly') and self.is_hourly:
            return -1 * (Decimal(self.hourly_rate * self.hours_per_period * self.period) / Decimal(period_to_use))
        else:
            return -1 * ((Decimal(self.value) * Decimal(self.period)) / Decimal(period_to_use))


class ALIncomeList(DAList):
    """Represents a filterable DAList of income items, each of which has an associated period or hourly wages."""
    
    def init(self, *pargs, **kwargs):
        self.elements = list()
        if not hasattr(self, 'object_type'):
            self.object_type = ALIncome
        return super(ALIncomeList, self).init(*pargs, **kwargs)        
    def types(self):
        """Returns a set of the unique types of values stored in the list."""
        types = set()
        for item in self.elements:
            if hasattr(item,'type'):
                types.add(item.type)
        return types

    def owners(self, type=None):
        """Returns a set of the unique owners for the specified type of value stored in the list. If type is None, returns all 
        unique owners in the ALIncomeList"""
        owners=set()
        if type is None:
            for item in self.elements:
                if hasattr(item, 'owner'):
                    owners.add(item.owner)
        elif isinstance(type, list):
            for item in self.elements:
                if hasattr(item,'owner') and hasattr(item,'type') and item.type in type:
                    owners.add(item.owner)
        else:
            for item in self.elements:
                if hasattr(item,'owner') and item.type == type:
                    owners.add(item.owner)
        return owners

    def matches(self, type):
        """Returns an ALIncomeList consisting only of elements matching the specified ALIncome type, assisting in filling PDFs with predefined spaces. Type may be a list"""
        if isinstance(type, list):
            return ALIncomeList(elements = [item for item in self.elements if item.type in type])
        else:
            return ALIncomeList(elements = [item for item in self.elements if item.type == type])

    def total(self, period_to_use=1, type=None,owner=None):
        """Returns the total periodic value in the list, gathering the list items if necessary.
        You can specify type, which may be a list, to coalesce multiple entries of the same type.
        Similarly, you can specify owner."""
        self._trigger_gather()
        result = 0
        if period_to_use == 0:
            return(result)
        if type is None:
            for item in self.elements:
                #if self.elements[item].exists:
                result += Decimal(item.amount(period_to_use=period_to_use))
        elif isinstance(type, list):
            for item in self.elements:
                if item.type in type:
                    if owner is None: # if we don't care who the owner is
                        result += Decimal(item.amount(period_to_use=period_to_use))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(period_to_use=period_to_use))
        else:
            for item in self.elements:
                if item.type == type:
                    if owner is None:
                        result += Decimal(item.amount(period_to_use=period_to_use))
                    else:
                        if not (isinstance(owner, DAEmpty)) and item.owner == owner:
                            result += Decimal(item.amount(period_to_use=period_to_use))
        return result
    
    def market_value_total(self, type=None):
        """Returns the total market value of values in the list."""
        result = 0
        for item in self.elements:
            if type is None:
                result += Decimal(item.market_value)
            elif isinstance(type, list): 
                if item.type in type:
                    result += Decimal(item.market_value)
            else:
                if item.type == type:
                    result += Decimal(item.market_value)
        return result


    def balance_total(self, type=None):
        self._trigger_gather()
        result = 0
        for item in self.elements:
            if type is None:
                result += Decimal(item.balance)
            elif isinstance(type, list): 
                if item.type in type:
                    result += Decimal(item.balance)
            else:
                if item.type == type:
                    result += Decimal(item.balance)
        return result
    
    def to_json(self):
        """Creates income list suitable for Legal Server API"""
        return json.dumps([{"type": income.type, "frequency": income.period, "amount": income.value} for income in self.elements])


class ALJob(ALIncome):
    """Represents a job that may be hourly or pay-period based. If non-hourly, may specify gross and net income amounts"""
    def net_amount(self, period_to_use=1):
        """Returns the net amount (e.g., minus deductions). Only applies if value is non-hourly."""
        return (Decimal(self.net) * Decimal(self.period)) / Decimal(period_to_use)
 
    def gross_amount(self, period_to_use=1):
        """Gross amount is identical to value"""
        return self.amount(period_to_use = period_to_use)

    def name_address_phone(self):
        """Returns concatenation of name, address and phone number of employer"""
        return self.employer + ': ' + self.employer_address + ', ' + self.employer_phone
    
    def normalized_hours(self, period_to_use):
        """Returns the number of hours worked in a given period"""
        return (float(self.hours_per_period) * int(self.period)) / int(period_to_use)


class ALJobList(ALIncomeList):
    """Represents a list of jobs. Adds the net_total and gross_total methods to the ALIncomeList class"""
    def init(self, *pargs, **kwargs):
        # self.elements = list()
        super(ALJobList, self).init(*pargs, **kwargs)        
        self.object_type = ALJob
    
    def gross_total(self, period_to_use=1, type=None):
        self._trigger_gather()
        result = 0
        if period_to_use == 0:
            return(result)
        if type is None:
            for item in self.elements:
                #if self.elements[item].exists:
                result += Decimal(item.gross_amount(period_to_use=period_to_use))
        elif isinstance(type, list):
            for item in self.elements:
                if item.type in type:
                    result += Decimal(item.gross_amount(period_to_use=period_to_use))
        else:
            for item in self.elements:
                if item.type == type:
                    result += Decimal(item.gross_amount(period_to_use=period_to_use))
        return result
    def net_total(self, period_to_use=1, type=None):
        self._trigger_gather()
        result = 0
        if period_to_use == 0:
            return(result)
        if type is None:
            for item in self.elements:
                #if self.elements[item].exists:
                result += Decimal(item.net_amount(period_to_use=period_to_use))
        elif isinstance(type, list):
            for item in self.elements:
                if item.type in type:
                    result += Decimal(item.net_amount(period_to_use=period_to_use))
        else:
            for item in self.elements:
                if item.type == type:
                    result += Decimal(item.net_amount(period_to_use=period_to_use))
        return result


class ALSimpleValue(DAObject):
    """Like a Value object, but no fiddling around with .exists attribute because it's designed to store in a list, not a dictionary"""
    def amount(self):
        """If desired, to use as a ledger, values can be signed. setting transaction_type = 'expense' makes the value negative. Use min=0 in that case."""
        if hasattr(self, 'transaction_type'):
            return (self.value * -1) if (self.transaction_type == 'expense') else self.value
        else:
            return self.value

    def __str__(self):
        return str(self.amount())


class ALValueList(DAList):
    """Represents a filterable DAList of SimpleValues"""
    def init(self, *pargs, **kwargs):
        super(ALValueList, self).init(*pargs, **kwargs)
        self.object_type = ALSimpleValue        

    def types(self):
        """Returns a set of the unique types of values stored in the list. Will fail if any items in the list leave the type field unspecified"""
        types = set()
        for item in self.elements:
            if hasattr(item,'type'):
                types.add(item.type)
        return types
        
    def total(self, type=None):
        """Returns the total value in the list, gathering the list items if necessary.
        You can specify type, which may be a list, to coalesce multiple entries of the same type."""
        self._trigger_gather()
        result = 0
        if type is None:
            for item in self.elements:
                #if self.elements[item].exists:
                result += Decimal(item.amount())
        elif isinstance(type, list):
            for item in self.elements:
                if item.type in type:
                    result += Decimal(item.amount())
        else:
            for item in self.elements:
                if item.type == type:
                    result += Decimal(item.amount())
        return result


class ALLedger(ALValueList):
    """Represents an account ledger. Adds calculate method which adds a running total to the ledger."""
    def init(self, *pargs, **kwargs):
        super(ALLedger, self).init(*pargs, **kwargs)              

    def calculate(self):
        """ Sort the ledger by date, then add a running total to each ledger entry"""
        self.elements.sort(key=lambda y: y.date)
        running_total = 0
        for entry in self.elements:
            running_total += entry.amount()
            entry.running_total = running_total


class ALVehicle(ALSimpleValue):
    """Vehicles have a method year_make_model() """
    def year_make_model(self):
        return self.year + ' / ' + self.make + ' / ' + self.model


class ALVehicleList(ALValueList):
    """List of vehicles, extends ALValueList. Vehicles have a method year_make_model() """
    def init(self, *pargs, **kwargs):
        super(ALVehicleList, self).init(*pargs, **kwargs)
        self.object_type = ALVehicle


class ALAsset(ALIncome):
  """
  Like income but with an optional value.
  """
  def amount(self, period_to_use=1):
    if not hasattr(self, 'value'):
      return 0
    else:
      return super(ALAsset, self).amount(period_to_use=period_to_use)


class ALAssetList(ALIncomeList):
      def init(self, *pargs, **kwargs):
        super(ALAssetList, self).init(*pargs, **kwargs)  
        self.object_type = ALAsset
