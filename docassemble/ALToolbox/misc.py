import docassemble.base.functions
from docassemble.base.util import defined, value, showifdef, space_to_underscore
import re

class shortenMe:
  def __init__(self, originalURL):
    self.shortenedURL = docassemble.base.functions.temp_redirect(originalURL, 60*60*24*7, False, False)
 
 #The following three functions are from Quinten
#format a float number to a whole number with thousands separator
def thousands(num:float, show_decimals=False) -> str:
  """
  Return a whole number formatted with thousands separator.
  Optionally, format with 2 decimal points (for a PDF form with the 
  currency symbol already present in the form)
  """
  try:
    if show_decimals:
      return f"{num:,.2f}"
    else:
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

def collapse_template(template, classname=None):
  """
  Insert HTML for a Bootstrap "collapse" div.
  """
  if classname is None:
      classname = ' bg-light'
  else:
      classname = ' ' + classname.strip()
  the_id = re.sub(r'[^A-Za-z0-9]', '', template.instanceName)
  return """\
<a class="collapsed" data-bs-toggle="collapse" href="#{}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="pdcaretclosed"><i class="fas fa-caret-right"></i></span> {}</a>
<div class="collapse" id="{}"><div class="card card-body{} pb-1">{}</div></div>\
""".format(the_id, template.subject_as_html(trim=True), the_id, classname, template.content_as_html())

def display_template(template, scrollable=True, class_name=None):
  """
  Display the subject and content of a markdown template in a scrollable way.
  """
  if scrollable:
    scroll_class = 'scrollable-panel'
  else:
    scroll_class = ''

  if class_name is None:
      class_name = ' bg-light'
  else:
      class_name = ' ' + class_name.strip()
  the_id = re.sub(r'[^A-Za-z0-9]', '', template.instanceName)
  return """\
<div class="{} card card-body{} pb-1" id="{}"><div class="panel-heading"><h3>{}</h3></div>{}</div>\
""".format(scroll_class, class_name, the_id, template.subject_as_html(trim=True), template.content_as_html())
  
def tabbed_templates_html(tab_group_name:str, *pargs)->str:
  """
  Provided a list of templates, create Bootstrap v 4.5 tabs with the `subject` as the tab label.
  """
  if isinstance(tab_group_name, str):
    tab_group_name = space_to_underscore(tab_group_name)  
  else:
    tab_group_name = "tabbed-group"
  tabs = f'<ul class="nav nav-tabs" id="{tab_group_name}" role="tablist">\n'
  tab_content = '<div class="tab-content" id="myTabContent">'
  for index, templ in enumerate(pargs):
    tab_id = space_to_underscore(str(templ.subject))
    tabs += '<li class="nav-item" role="presentation">\n'
    if index == 0:
      tabs += f'<a class="nav-link active" id="{tab_group_name}-{tab_id}-tab" data-bs-toggle="tab" href="#{tab_group_name}-{tab_id}" role="tab" aria-controls="{tab_id}" aria-selected="true">{templ.subject}</a>\n'
      tab_content += f'<div class="tab-pane fade show active" id="{tab_group_name}-{tab_id}" role="tabpanel" aria-labelledby="{tab_group_name}-{tab_id}-tab">\n'
      tab_content += templ.content_as_html()
      tab_content += '\n</div>\n'      
    else:
      tabs += f'<a class="nav-link" id="{tab_group_name}-{tab_id}-tab" data-bs-toggle="tab" href="#{tab_group_name}-{tab_id}" role="tab" aria-controls="{tab_id}" aria-selected="false">{templ.subject}</a>\n'
      tab_content += f'<div class="tab-pane fade" id="{tab_group_name}-{tab_id}" role="tabpanel" aria-labelledby="{tab_group_name}-{tab_id}-tab">\n'
      tab_content += templ.content_as_html()
      tab_content += '\n</div>\n'
    tabs += '</li>'
  tabs += '</ul>'
  tab_content += '</div>'  
  
  return tabs + tab_content

def sum_if_defined(*pargs):
  """Lets you add up the value of variables that are not in a list"""
  total = 0
  for source in pargs:
    if defined(source):
      total += value(source)
  return total

def add_records(obj, labels):
  """ List demo interviews in the current package to be run from the landing page """
  index = 0
  for key, val in labels.items():      
    obj.appendObject()
    obj[index].name = key
    obj[index].description = val[0]
    obj[index].reference = val[1]
    index += 1
  return obj  