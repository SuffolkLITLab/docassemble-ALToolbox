import re
from docassemble.base.util import CustomDataType, DAValidationError

class PhoneNumber( CustomDataType ):
    name = 'phone'
    input_class = 'dal-phone'
    javascript = """\
/* # Resources
*  1. What we're using: https://github.com/jackocnr/intl-tel-input
*  1. Especially see: https://github.com/jackocnr/intl-tel-input#static-methods getInstance
*  1. https://www.npmjs.com/package/google-libphonenumber
*  1. https://github.com/google/libphonenumber/blob/master/FALSEHOODS.md
*  1. source: https://www.sitepoint.com/working-phone-numbers-javascript/
*/

// Immediate client side validation (add to jQuery validator)
// https://intl-tel-input.com/node_modules/intl-tel-input/examples/gen/is-valid-number.html
let validatePhoneNumber = function( value, element, params ) {
  console.log( 'params', params );
  if ( value.trim() ) {
    let telLibObj = window.intlTelInputGlobals.getInstance( element );
    if ( telLibObj.isValidNumber() ) { return true; }
  }
  // If any of those didn't pass
  return false;
};

$.validator.addMethod( 'phone', validatePhoneNumber );
"""
    jq_rule = 'phone'
    jq_message = 'You need to enter a valid phone number.'
    
    # No server-side validation. Just avoiding user error here.
    # If you want to discuss that decision, flag someone else for that.
