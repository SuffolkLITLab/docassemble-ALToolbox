from docassemble.base.functions import word, log

# See GitHub issue https://github.com/SuffolkLITLab/docassemble-ALToolbox/issues/16
def share_button (
  text_to_copy,
  text_before='',
  label='Copy',
  tooltip_inert_text='Copy to clipboard',
  tooltip_copied_text='Copied: '  # Will have `text_to_copy` added to it
):
  '''Return the html for a button that will let a user share the given text'''
  button_str = '<div class="al_share">\n'
  if ( text_before != '' ):
    button_str += f'<span class="al_share_description">{word( text_before )}</span>\n'
  button_str += f'<input readonly class="al_share_value" type="text" value="{word( text_to_copy )}">\n'
  button_str += f'<button class="btn btn-primary al_share_button" type="button">\n'
  button_str += f'<span class="al_tooltip al_tooltip_inert">{word( tooltip_inert_text )}</span>\n'
  
  if ( tooltip_copied_text == 'Copied: ' ):
    # Our default text will show 'Copied: text that will be copied'
    button_str += f'<span class="al_tooltip al_tooltip_active">Copied: {word( tooltip_copied_text ) + text_to_copy }</span>\n'
  else:
    # Otherwise, use the custom text handed in
    button_str += f'<span class="al_tooltip al_tooltip_active">Copied: {word( tooltip_copied_text )}</span>\n'
  
  button_str += f'<i class="far fa-copy"></i>\n'
  button_str += f'<span>{ label }</span>\n'
  button_str += f'</div>\n'
  
  return button_str
