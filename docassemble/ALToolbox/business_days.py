import holidays
import pandas as pd
import datetime
from datetime import date as dt
from docassemble.base.util import as_datetime, DADateTime
from typing import Union

"""
  External docs: 
  1. https://github.com/dr-prodigy/python-holidays (holidays module v0.13, as of 2/2022)
  2. https://python-holidays.readthedocs.io/en/latest/examples.html  
  3. https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html  
"""


def standard_holidays(
    year, country="US", subdiv="MA", add_holidays=None, remove_holidays=None
) -> dict:
    # 1. Get standard holidays from python's holidays module
    countr_holidays = []
    countr_holidays = holidays.country_holidays(
        country=country, subdiv=subdiv, years=year
    )

    # 2. Remove known obsolete holidays
    if country == "US" and subdiv == "MA":
        countr_holidays.pop_named("Evacuation Day")

    # 3. Remove user specified holidays
    if remove_holidays:
        for record in remove_holidays:
            countr_holidays.pop_named(record)

    # 4. Append user defined holidays
    if add_holidays:
        for k, v in add_holidays.items():
            # Attach the given year to the key
            key = f"{year}-{k}"
            countr_holidays[key] = v
    return countr_holidays


def non_business_days(
    year,
    country="US",
    subdiv="MA",
    add_holidays=None,
    remove_holidays=None,
    first_n_dates=0,
    last_n_dates=0,
) -> dict:
    # 1. Collect weekends and standard holidays
    # 1.1 Get all saturdays and sundays in the given year
    # Must use .strftime('%m/%d/%Y')to make it a string, otherwise will get 'TypeError'
    sundays = (
        pd.date_range(start=str(year), end=str(year + 1), freq="W-SUN")
        .strftime("%Y-%m-%d")
        .tolist()
    )
    saturdays = (
        pd.date_range(start=str(year), end=str(year + 1), freq="W-SAT")
        .strftime("%Y-%m-%d")
        .tolist()
    )

    # 1.2 Get holidays of the given country and subdivision (state/province) in the year
    local_holidays = standard_holidays(
        year=year,
        country=country,
        subdiv=subdiv,
        add_holidays=add_holidays,
        remove_holidays=remove_holidays,
    )

    # 2. Populate date_dict using as_datetime format as key for later sorting
    # 2.1 Populate date_dict with holidays
    date_dict = {}
    for raw_date, name in local_holidays.items():
        date_dict[as_datetime(raw_date)] = name

    # 2.2 Add weekends if not already in date_dict
    for a in saturdays:
        if as_datetime(a) not in date_dict.keys():
            date_dict[as_datetime(a)] = "Saturday"
    for b in sundays:
        if as_datetime(b) not in date_dict.keys():
            date_dict[as_datetime(b)] = "Sunday"

    # 3. Sort date_dict then change key from as_datetime to mm/dd/yyyy for easier application
    date_dict = dict(sorted(date_dict.items()))

    clean_date_dict = {}
    for k, v in date_dict.items():
        clean_date_dict[k.strftime("%Y-%m-%d")] = v

    # 4. Take a subset if user desires it (useful only if this function is explicitly called)
    final_output = {}
    if first_n_dates > 0 and last_n_dates > 0:
        first_slice = {
            s: clean_date_dict[s] for s in list(clean_date_dict)[:first_n_dates]
        }
        last_slice = {
            s: clean_date_dict[s]
            for s in list(clean_date_dict)[len(clean_date_dict.keys()) - last_n_dates :]
        }
        final_output = {**first_slice, **last_slice}  # Add two dicts
    elif first_n_dates > 0:
        final_output = {
            s: clean_date_dict[s] for s in list(clean_date_dict)[:first_n_dates]
        }
    elif last_n_dates > 0:
        final_output = {
            s: clean_date_dict[s]
            for s in list(clean_date_dict)[len(clean_date_dict.keys()) - last_n_dates :]
        }
    else:
        final_output = clean_date_dict

    # 5. Return the result
    return final_output


def is_business_day(
    date: Union[str, DADateTime],
    country="US",
    subdiv="MA",
    add_holidays=None,
    remove_holidays=None,
) -> bool:
    if not isinstance(date, DADateTime):
        date = as_datetime(date)
    if date.dow in [
        6,
        7,
    ]:  # Docassemble codes Saturday and Sunday as 6 and 7 respectively
        return False
    if date.format("yyyy-MM-dd") in standard_holidays(
        year=date.year,
        country=country,
        subdiv=subdiv,
        add_holidays=add_holidays,
        remove_holidays=remove_holidays,
    ):
        return False
    return True


def get_next_business_day(
    start_date: Union[str, DADateTime],
    wait_n_days=1,
    country="US",
    subdiv="MA",
    add_holidays=None,
    remove_holidays=None,
) -> DADateTime:
    """
    Returns the first day AFTER the specified start date that is
    not a holiday, Saturday or Sunday.
    """
    if not isinstance(start_date, DADateTime):
        start_date = as_datetime(start_date)
    date_to_check = start_date.plus(days=wait_n_days)

    while not is_business_day(
        date_to_check,
        country=country,
        subdiv=subdiv,
        add_holidays=add_holidays,
        remove_holidays=remove_holidays,
    ):
        date_to_check = date_to_check.plus(days=1)
    return date_to_check
