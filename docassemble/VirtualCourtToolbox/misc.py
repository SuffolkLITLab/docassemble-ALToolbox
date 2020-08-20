#This is Jonathan's code, we just added a wrapper.
import docassemble.base.functions
class shortenMe:
  def __init__(self, originalURL):
    self.shortenedURL = docassemble.base.functions.temp_redirect(originalURL, 60*60*24*7, False, False)
 
  # This function triggers server-side validation.
#from docassemble.base.util import as_datetime
#from docassemble.base.functions import log
#class is_date_valid:
#  def __init__(self, aDate):
#    log( 'init', 'console' )
#    # Try to change string into DADateTime
#    try:
#      as_datetime( aDate )
#      self.valid = True
#    # If error, date is not a valid DADateTime (out of range, usually)
#    except:
#      self.valid = False
#    
#    log( self.valid, 'console' )
    

# This function triggers server-side validation.
from docassemble.base.util import as_datetime, log
#from docassemble.base.functions import log
log( 'blah', 'console' )
def is_valid_date( aDate ):
  valid = False
  #log( 'start' )
  log( 'start', 'console' )
  # Try to change string into DADateTime
  try:
    as_datetime( aDate )
    valid = True
  # If error, date is not a valid DADateTime (out of range, usually)
  except:
    valid = False
    
  #log( valid )
  log( valid, 'console' )

  return valid
    