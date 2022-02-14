import holidays  
import pandas as pd
import datetime 
from datetime import date as dt  
from docassemble.base.util import as_datetime
"""
  External docs: 
  1. https://github.com/dr-prodigy/python-holidays
  2. https://pypi.org/project/holidays/
  3. https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html
  Note:
  There seems to be a core issue in holidays module, where if you delete a holiday cross the year, it will add in holidays from the previous year in error. For example, 
      12/31/2021: New Year’s Day (Observed) and 01/01/2022: New Year’s Day 
  are both included in 2022 holidays. If remove_holidays=['new year'], then after this line of code:
      local_holidays.pop_named(record) 
  the results will erroneously include 2021's holidays as well. But practically no one would delete New Year anyway, we should be fine and there is no need to alarm the user about this issue.
"""
def non_business_days(start_date, add_n_days=0, country='US', state='MA', province=None, add_holidays=None, remove_holidays=None, first_n_dates=0) -> dict:      
  # 1. Collect weekends, standard holidays and user defined add/remove holidays
  # 1.1 Get all saturdays and sundays in the given year  
  date = as_datetime(start_date)
  year = date.year
  # Must use .strftime('%m/%d/%Y')to make it a string, otherwise will get 'TypeError'
  sundays = pd.date_range(start=str(year), end=str(year+1), freq='W-SUN').strftime('%m/%d/%Y').tolist()
  saturdays = pd.date_range(start=str(year), end=str(year+1), freq='W-SAT').strftime('%m/%d/%Y').tolist()  

  # 1.2 Get holidays of the given state/province and country in the year
  local_holidays = holidays.CountryHoliday(country=country, prov=province, state=state, years=year) 

  # 1.3 Remove known obsolete holidays 
  if country == 'US' and state == 'MA':
    local_holidays.pop_named("Evacuation Day")  

  # 1.4 Remove user defined holidays     
  if remove_holidays:
    for record in remove_holidays:        
      local_holidays.pop_named(record)   

  # 1.5 Append user defined holidays   
  if add_holidays: 
    for k, v in add_holidays.items():
      local_holidays[k] = v

  # 2. Populate date_dict using as_datetime format as key for later sorting
  # 2.1 Populate date_dict with holidays 
  date_dict = {}
  for raw_date, name in local_holidays.items():          
    date_dict[as_datetime(raw_date)] = name

  # 2.2 Add weekends if not already in date_dict
  for a in saturdays:
    if as_datetime(a) not in date_dict.keys():
      date_dict[as_datetime(a)] = 'Saturday'
  for b in sundays:
    if as_datetime(b) not in date_dict.keys():
      date_dict[as_datetime(b)] = 'Sunday'     

  # 3. Sort date_dict then change key from as_datetime to mm/dd/yyyy for easier application
  date_dict = dict(sorted(date_dict.items()))
  clean_date_dict = {}
  for k, v in date_dict.items():     
    clean_date_dict[k.strftime('%m/%d/%Y')] = v

  # 4. Take a subset if user desires it (useful only if this function is explicitly called)
  if first_n_dates > 0:
    final_output = {s: clean_date_dict[s] for s in list(clean_date_dict)[:first_n_dates]}    
  else:
    final_output = clean_date_dict      

  #5. Return the result  
  return final_output
	
def is_business_day(start_date, add_n_days=0, country='US', state='MA', province=None, add_holidays=None, remove_holidays=None) -> bool:  
  end_date = (as_datetime(start_date) + datetime.timedelta(days=add_n_days)).strftime('%m/%d/%Y')    
  if end_date in non_business_days(start_date, add_n_days=add_n_days, country=country, state=state, province=province, add_holidays=add_holidays, remove_holidays=remove_holidays).keys():
    return False
  else: 
    return True
  
def get_next_business_day(start_date, add_n_days=0, country='US', state='MA', province=None, add_holidays=None, remove_holidays=None) -> dt:	
  index = add_n_days    
  done = False
  while not done: 
    new_date = (as_datetime(start_date) + datetime.timedelta(days=index)).strftime('%m/%d/%Y')
    done = is_business_day(start_date=new_date, country=country, state=state, province=province, add_holidays=add_holidays, remove_holidays=remove_holidays)
    index += 1
  return new_date 