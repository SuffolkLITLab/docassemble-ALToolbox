#This is Jonathan's code, we just added a wrapper.
import docassemble.base.functions
class shortenMe:
  def __init__(self, originalURL):
    self.shortenedURL = docassemble.base.functions.temp_redirect(originalURL, 60*60*24*7, False, False)
 
 #The following three functions are from Quinten
#format a float number to a whole number with thousands separator
def thousands(num:float) -> str:
  """
  Return a whole number formatted with thousands separator.
  """
  try:
    return f"{int(num):,}"
  except:
    return num

#Format a phone number so you can click on it to open in your phone dialer
def tel(phone_number):
  return '<a href="tel:' + str(phone_number) + '">' + str(phone_number) + "</a>"

#Display an icon on the screen.
def fa_icon(icon, color="primary", color_css=None, size="sm"):
  """
  Return HTML for a font-awesome icon of the specified size and color. You can reference
  a CSS variable (such as Bootstrap theme color) or a true CSS color reference, such as 'blue' or 
  '#DDDDDD'. Defaults to Bootstrap theme color "primary".
  """
  if not color and not color_css:
    return ':' + icon + ':' # Default to letting Docassemble handle it
  elif color_css:
    return '<i class="fa fa-' + icon + ' fa-' + size + '" style="color:' + color_css + ';"></i>'
  else:
    return '<i class="fa fa-' + icon + ' fa-' + size + '" style="color:var(--' + color + ');"></i>'
  