#This is Jonathan's code, we just added a wrapper.
import docassemble.base.functions
class shortenMe:
  def __init__(self, originalURL):
    self.shortenedURL = docassemble.base.functions.temp_redirect(originalURL, 60*60*24*7, False, False)
   
 #This function triggers client side validation.
from docassemble.base.util import month_of, day_of, year_of
class is_date_valid:
  def __init__(self,aDate):
    month = month_of(aDate) 
    day = day_of(aDate)
    year = year_of(aDate)    
    day_count_for_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    #check leap year and reset its day
    if year%4==0 and (year%100 != 0 or year%400==0):
      day_count_for_month[2] = 29
    #Output
    self.valid = (1 <= month <= 12 and 1 <= day <= day_count_for_month[month])  