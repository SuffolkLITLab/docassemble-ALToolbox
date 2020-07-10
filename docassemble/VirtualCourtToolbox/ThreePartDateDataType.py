from docassemble.base.util import CustomDataType, DAValidationError, word, as_datetime
import re

class ThreePartDateDataType( CustomDataType ):
    name = 'textdate'
    input_type = 'textdate'
    jq_rule = 'textdate'
    jq_message = word("This date doesn't look right")
    @classmethod
    def validate(cls, aDate):
      # Try to change string into DADateTime
      try:
        as_datetime( aDate )
        return True
      # If error, date is not a valid DADateTime
      except:
        return False
