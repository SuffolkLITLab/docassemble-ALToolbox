import re
from docassemble.base.util import CustomDataType, DAValidationError

__all__ = ["PhoneNumber"]


class PhoneNumber(CustomDataType):
    name = "al_international_phone"
    input_class = "al_international_phone"
    javascript = """\
/** When combined with the phone number javascript file shown in
*    phone_number_validation_demo.yml, this docassemble CustomDataType
*    will make sure a user has give valid phone numbers in input fields
*    with the `datatype` `al_international_phone`. This includes international
*    numbers.
*
* This docassemble CustomDataType will be installed on your server along
*    with the ALToolbox package. Like all docassemble CustomDataTypes, it
*    will always be active on your server as long as it's there.
*    
* ## More Resources
*    1. What we're using: https://github.com/jackocnr/intl-tel-input
*    1. It uses https://www.npmjs.com/package/google-libphonenumber
*    1. https://github.com/google/libphonenumber/blob/master/FALSEHOODS.md
*    1. https://github.com/google/libphonenumber/blob/master/FAQ.md
*/
var validatePhoneNumber = function( value, element, params ) {
  /** Returns true if the international phone number is valid or if the field
  *    is empty. Otherwise returns false.
  */
  // When a field is empty, this value will be '', which counts as `false` here
  if ( value.trim() ) {
    // We can't use window.intlTelInputGlobals.loadUtils. It lets us
    // validate numbers docassemble has formatted, but only the first time
    // The user hits 'Back'. After that, the numbers are seen as invalid.
    
    // Get the special field that has already been created during page load
    var telLibObj = window.intlTelInputGlobals.getInstance( element );
    // Validate its value when the form is submitted
    return telLibObj.isValidNumber();
  }
  // If it's an empty field, then it's valid as far as this is concerned.
  return true;
};

$.validator.addMethod( 'al_international_phone', validatePhoneNumber );
"""
    jq_rule = "al_international_phone"
    # People that have just entered an invalid US phone number could find this confusing
    jq_message = 'This phone number doesn\'t look right. Note that a non-US number needs a "+" before the number.'

    # No server-side validation. Just avoiding user error here.
    # If you want to discuss that decision, make an issue on the repository.
