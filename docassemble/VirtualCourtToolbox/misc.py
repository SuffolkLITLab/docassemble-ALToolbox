#This is Jonathan's code, we just added a wrapper.
import docassemble.base.functions
class shortenMe:
  def __init__(self, originalURL):
    self.shortenedURL = docassemble.base.functions.temp_redirect(originalURL, 60*60*24*7, False, False)
   
 #This function triggers client side validation.
from docassemble.base.util import as_datetime
class is_date_valid:
  def __init__(self, aDate):
    # Try to change string into DADateTime
    try:
      as_datetime( aDate )
      self.valid = True
    # If error, date is not a valid DADateTime (out of range, usually)
    except:
      self.valid = False
    