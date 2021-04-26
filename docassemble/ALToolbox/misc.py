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

def space(var_name, prefix=' ', suffix=''):
  """If the value as a string is defined, return it prefixed/suffixed. Defaults to prefix
  of a space. Helps build a sentence with less cruft. Equivalent to SPACE function in
  HotDocs."""
  if var_name and isinstance(var_name, str) and re.search(r'[A-Za-z][A-Za-z0-9\_]*', var_name) and defined(var_name) and value(var_name):
    return prefix + showifdef(var_name) + suffix
  else:
    return ''  

def yes_no_unknown(var_name, condition, unknown="Unknown", placeholder=0):
  """Return 'unknown' if the value is None rather than False. Helper for PDF filling with
  yesnomaybe fields"""
  if condition:
    return value(var_name)
  elif condition is None:
    return unknown
  else:
    return placeholder

def number_to_letter(n):
  """Returns a capital letter representing ordinal position. E.g., 1=A, 2=B, etc. Appends letters
  once you reach 26 in a way compatible with Excel/Google Sheets column naming conventions. 27=AA, 28=AB...
  """
  string = ""
  if n is None:
    n = 0
  while n > 0:
    n, remainder = divmod(n - 1, 26)
    string = chr(65 + remainder) + string
  return string
