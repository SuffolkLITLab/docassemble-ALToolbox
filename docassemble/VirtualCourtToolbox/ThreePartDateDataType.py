from docassemble.base.util import CustomDataType, DAValidationError, word, as_datetime
import re

class ThreePartDateDataType( CustomDataType ):
    name = 'textdate'
    input_type = 'textdate'
    javascript = """\
$.validator.addMethod('textdate', function(value, element, params){
  var parsed = Date.parse( value );
  if ( isNaN( parsed ) ) { return false; }
  // Otherwise use another way to make sure that the date was a valid date
  // That is, if the user enters '02/31/2020', it doesn't return `NaN`, but
  // it does return May 2nd. We can check for that change.
  else {
    // Format the values the same so they can be compared
    var newDate = new Date( value );
    var newDateParts = [
      parseInt( newDate.getMonth() + 1 ),  // it starts as index of month
      parseInt( newDate.getDate()),
      parseInt( newDate.getFullYear()),
    ];
    var oldDateParts = value.split( '/' );
    oldDateParts.forEach( function( part, index, dateParts ) {
      dateParts[ index ] = parseInt( part );
    });

    if ( JSON.stringify( newDateParts ) === JSON.stringify( oldDateParts )) {
      return true;
    } else {
      return false;
    }
  }
});
"""
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
