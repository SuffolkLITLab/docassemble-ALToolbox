import holidays
import pandas as pd
import datetime
from datetime import date as dt
from docassemble.base.util import as_datetime, DADateTime
from typing import Union, Dict, Iterable, Mapping, Optional

"""
  External docs: 
  1. https://github.com/dr-prodigy/python-holidays (holidays module v0.13, as of 2/2022)
  2. https://python-holidays.readthedocs.io/en/latest/examples.html  
  3. https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html  
"""

__all__ = [
    "standard_holidays",
    "non_business_days",
    "is_business_day",
    "get_next_business_day",
    "get_date_after_n_business_days",
]


def standard_holidays(
    year,
    country="US",
    subdiv="MA",
    add_holidays: Optional[Mapping] = None,
    remove_holidays: Optional[Iterable[str]] = None,
) -> holidays.HolidayBase:
    """
    Get all holidays in the specified year, country, and state (or other subdivision).
    Note that this draws on the "holidays" package which may deviate slightly from
    holidays observed by a local court, but should be very close to accurate.

    Returns a dictionary like-object that you can treat like:

    ```
    {
        "2021-01-01": "New Year's Day",
        ...
        "2021-12-25": "Christmas Day",
    }
    ```

    In place of a string, the object that is returned can also be treated as though
    the keys are datetime.date objects.

    Arguments:
        year: the year to get holidays for
        country: the country to use holidays from (default: "US")
        subdiv: the subdivision (e.g. state or province) to use holidays from (default: "MA")
        add_holidays: a dictionary from date strings ("12-25") to the name of the holiday, to add custom holidays
        remove_holidays: a list of holiday name strings to remove from the standard holidays

    Examples:
        ```python
        # Get standard holidays for Massachusetts in 2023
        ma_holidays = standard_holidays(2023)
        print(ma_holidays["2023-07-04"])  # Independence Day

        # Get holidays for a different state
        ca_holidays = standard_holidays(2023, country="US", subdiv="CA")

        # Add custom holidays
        custom_holidays = standard_holidays(
            2023, 
            add_holidays={"03-17": "Company Founding Day"}
        )
        print(custom_holidays["2023-03-17"])  # Company Founding Day

        # Remove holidays that your court doesn't observe
        court_holidays = standard_holidays(
            2023,
            remove_holidays=["Columbus Day", "Veterans Day"]
        )
        ```
    """
    # 1. Get standard holidays from python's holidays module
    countr_holidays: holidays.HolidayBase = holidays.country_holidays(
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
    add_holidays: Optional[Mapping] = None,
    remove_holidays: Optional[Iterable[str]] = None,
    first_n_dates=0,
    last_n_dates=0,
) -> dict:
    """
    Get all non-business days (weekends and holidays) in the specified year, country, and state. 
    This function returns a dictionary of all dates that are not business days, including 
    both weekends (Saturdays and Sundays) and official holidays.

    Arguments:
        year: the year to get non-business days for
        country: the country to use holidays from (default: "US")
        subdiv: the subdivision (e.g. state or province) to use holidays from (default: "MA")
        add_holidays: a dictionary from date strings ("12-25") to the name of the holiday, to add custom holidays
        remove_holidays: a list of holiday name strings to remove from the standard holidays
        first_n_dates: if specified, only return the first N non-business days of the year
        last_n_dates: if specified, only return the last N non-business days of the year

    Returns:
        A dictionary where keys are date strings ("YYYY-MM-DD") and values are the name of the non-business day 
        (e.g., "Saturday", "New Year's Day").

    Examples:
        ```python
        # Get all non-business days for 2023
        all_non_business = non_business_days(2023)
        print(len(all_non_business))  # Shows total count of non-business days

        # Get just the first 10 non-business days of the year
        first_ten = non_business_days(2023, first_n_dates=10)

        # Get the last 5 non-business days of the year  
        last_five = non_business_days(2023, last_n_dates=5)

        # Get non-business days with custom holidays
        custom_non_business = non_business_days(
            2023,
            add_holidays={"03-17": "Company Founding Day"}
        )
        ```
    """
    # TODO: this function may not be necessary, but check with @purplesky2016 before removing
    # 1. Collect weekends and standard holidays
    # 1.1 Get all saturdays and sundays in the given year

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
    add_holidays: Optional[Mapping] = None,
    remove_holidays: Optional[Iterable[str]] = None,
) -> bool:
    """
    Returns true if and only if the specified date is a business day (i.e., not a holiday)
    in the specified jurisdiction. Business days are considered to be:
    1. weekdays other than Saturday and Sunday and
    1. days that are not a federal or state-observed holiday

    Arguments:
        date: the date to check. Can be a date-formatted string (i.e. "2023-03-26", or "3-26-2023") or a DADateTime object
        country: the country to use holidays from (default: "US")
        subdiv: the subdivision (e.g. state or province) to use holidays from (default: "MA")
        add_holidays: a dictionary from date strings ("12-25") to the name of the holiday, to add custom holidays
        remove_holidays: a list of holiday name strings to remove from the standard holidays

    Examples:
        ```python
        # Check if a specific date is a business day
        assert(is_business_day("2023-03-26") == False)  # Sunday

        # Check a weekday that's not a holiday
        assert(is_business_day("2023-03-27") == True)  # Monday

        # Check a holiday
        assert(is_business_day("2023-07-04") == False)  # Independence Day

        # Check with custom holidays
        is_company_day = is_business_day(
            "2023-03-17",
            add_holidays={"03-17": "Company Founding Day"}
        )
        assert(is_company_day == False)  # Custom holiday

        # Check for different jurisdiction
        is_business_uk = is_business_day("2023-12-26", country="UK")  # Boxing Day
        ```
    """
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
    add_holidays: Optional[Mapping] = None,
    remove_holidays: Optional[Iterable[str]] = None,
) -> DADateTime:
    """
    Returns the first day AFTER the specified start date that is
    not a federal or state holiday, Saturday or Sunday. Optionally,
    specify the parameter `wait_n_days` to get the first business day after
    at least, e.g., 10 days.

    Relies on the Python holidays package, which has fairly good support for
    holidays around the world and in various states and provinces, but local
    court rules may differ. You can see what holidays are used at
    https://github.com/dr-prodigy/python-holidays/tree/master/holidays/countries

    Arguments:
        start_date: the date to start with. Can be a date-formatted string (i.e. "2023-03-26", or
            "3-26-2023") or a DADateTime object
        wait_n_days: the number of days to find the find the date after. If 0, it returns the given
            date if it's a business day. (default: 1)
        country: the country to use business days from (default: "US")
        subdiv: the subdivision (e.g. state or province) to use business days from (default: "MA")
        add_holidays: a dictionary from date strings ("12-25") to the name of the holiday,
            to add custom holidays to be considered
        remove_holidays: a list of holiday name strings of dates that are no longer holidays

    Examples:
        ```python
        # Get the next business day after a Friday
        next_day = get_next_business_day("2023-03-24")  # Friday
        print(next_day)  # 2023-03-27 (Monday)

        # Get the first business day at least 5 days later
        later_day = get_next_business_day("2023-03-20", wait_n_days=5)
        print(later_day)  # First business day at least 5 days after March 20

        # Handle holidays - if the calculated day falls on a holiday, 
        # it will automatically find the next business day
        holiday_next = get_next_business_day("2023-07-03")  # Day before July 4th
        print(holiday_next)  # 2023-07-05 (skips July 4th holiday)

        # With custom holidays
        custom_next = get_next_business_day(
            "2023-03-16",
            add_holidays={"03-17": "Company Founding Day"}
        )
        # Will skip March 17th as it's now considered a holiday
        ```
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


def get_date_after_n_business_days(
    start_date: Union[str, DADateTime],
    wait_n_days=1,
    country="US",
    subdiv="MA",
    add_holidays: Optional[Mapping] = None,
    remove_holidays: Optional[Iterable[str]] = None,
) -> DADateTime:
    """
    Returns a time period which contains a minimum of `n` business days.

    Arguments:
        start_date: the date to start with. Can be a date-formatted string (i.e. "2023-03-26", or
            "3-26-2023") or a DADateTime object
        wait_n_days: the number of businesses days to wait for. For example, `start_date` is a
            Friday, and `wait_n_days` is 2, then the date returned will be the next Tuesday. (default: 1)
        country: the country to use business days from (default: "US")
        subdiv: the subdivision (e.g. state or province) to use business days from (default: "MA")
        add_holidays: a dictionary from date strings ("12-25") to the name of the holiday,
            to add custom holidays to be considered
        remove_holidays: a list of holiday name strings of dates that are no longer holidays

    Examples:
        ```python
        # Get the date after exactly 5 business days
        start_date = "2023-03-20"  # Monday
        result_date = get_date_after_n_business_days(start_date, wait_n_days=5)
        print(result_date)  # 2023-03-27 (Monday of next week)

        # Starting on a Friday, get date after 2 business days
        friday_start = "2023-03-24"  # Friday
        two_days_later = get_date_after_n_business_days(friday_start, wait_n_days=2)
        print(two_days_later)  # 2023-03-28 (Tuesday, skipping weekend)

        # Handle holidays automatically
        before_holiday = "2023-07-03"  # Monday before July 4th
        after_three_days = get_date_after_n_business_days(before_holiday, wait_n_days=3)
        print(after_three_days)  # 2023-07-07 (Friday, skipping July 4th holiday)

        # With custom holidays
        custom_result = get_date_after_n_business_days(
            "2023-03-15",
            wait_n_days=3,
            add_holidays={"03-17": "Company Founding Day"}
        )
        # Will count 3 business days, skipping weekends and custom holiday
        ```
    """
    if not isinstance(start_date, DADateTime):
        start_date = as_datetime(start_date)
    date_to_check = start_date

    for _ in range(wait_n_days):
        date_to_check = date_to_check.plus(days=1)
        while not is_business_day(
            date_to_check,
            country=country,
            subdiv=subdiv,
            add_holidays=add_holidays,
            remove_holidays=remove_holidays,
        ):
            date_to_check = date_to_check.plus(days=1)
    return date_to_check
