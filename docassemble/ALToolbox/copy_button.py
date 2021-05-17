from docassemble.base.functions import word, log

# See GitHub issue https://github.com/SuffolkLITLab/docassemble-ALToolbox/issues/16
def copy_button_html (
  text_to_copy:str,
  text_before:str='',
  label:str='Copy',
  tooltip_inert_text:str='Copy to clipboard',
  tooltip_copied_text:str='Copied!'
  )->str:
  '''Return the html for a button that will let a user copy the given text'''
  button_str = '<div class="al_copy">\n'
  if ( text_before != '' ):
    button_str += f'<span class="al_copy_description">{word( text_before )}</span>\n'
  button_str += f'<input readonly class="al_copy_value" type="text" value="{ text_to_copy }">\n'
  button_str += f'<button class="btn btn-primary al_copy_button" type="button">\n'
  button_str += f'<span class="al_tooltip al_tooltip_inert">{word( tooltip_inert_text )}</span>\n'
  button_str += f'<span class="al_tooltip al_tooltip_active">{word( tooltip_copied_text )}</span>\n'
  button_str += f'<i class="far fa-copy"></i>\n'
  button_str += f'<span>{word( label )}</span>\n'
  button_str += f'</div>\n'
  
  return button_str
