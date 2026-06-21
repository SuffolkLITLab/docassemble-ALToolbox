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
* A lot of code for validation was adapted from AL's ThreePartsDate fields.
*    
* ## More Resources
*    1. What we're using: https://github.com/jackocnr/intl-tel-input
*    1. It uses https://www.npmjs.com/package/google-libphonenumber
*    1. https://github.com/google/libphonenumber/blob/master/FALSEHOODS.md
*    1. https://github.com/google/libphonenumber/blob/master/FAQ.md
*/
try {

/** Uses jQuery validation plugin to set up validation functionality */
$(document).on(`daPageLoad`, function(){
 $('input.al_international_phone').each(function( field_i, field ){
    let rules = {
      phoneValidInput: true,
      messages: {
        phoneValidInput: showInvalidInputMessage
      }
    };
    $(field).rules(`add`, rules);
  });
});  // ends on da page load

function validatePhoneNumber( value, element, params ) {
  /** Returns true if the international phone number is valid or if the field
   *    is empty. Otherwise returns false.
   * 
   * @param value {string} - value of the input field
   * @param element {HTML node} - HTML node of the field
   * @param params {*} - An object (presumably containing field properties)
   * 
   * @returns {bool} - True if the field value is valid, otherwise `false`
   */
  // When a field is empty, this value will be '', which counts as `false` here
  if ( value.trim() ) {
    // We can't use window.intlTelInputGlobals.loadUtils. It lets us
    // validate numbers docassemble has formatted, but only the first time
    // The user hits 'Back'. After that, the numbers are seen as invalid.
    
    // Get the special field that has already been created during page load
    var telLibObj = window.intlTelInput.getInstance( element );
    // Validate its value when the form is submitted
    return telLibObj.isValidNumberPrecise();
  }
  // If it's an empty field, then it's valid as far as this is concerned.
  return true;
};


/**
 * If the input is invalid, show the correct message for the type of invalidity.
 * 
 * Custom validation message: https://stackoverflow.com/a/75202524
 * 
 * @param {*} params - Parameters we would pass in via the DOM if we had control.
 * @param {HTML node} field - HTML node for field that is being validated.
 * 
 * @returns {string} - Message to show if the field is invalid
 */
function showInvalidInputMessage( params, field ) {
  return (
    $(field).attr('data-alInvalidInputMessage')
    // The default message could be confusing for invalid US phone numbers
    || `This phone number doesn't look right. Note that a non-US number needs a "+" before the number.`
  )
};

$.validator.addMethod( `phoneValidInput`, validatePhoneNumber );
  
} catch ( phoneNumberFieldError ) {
  console.error(`This won't log to the console. If you see this, though, it's coming from PhoneNumberDataType.py`, phoneNumberFieldError );
}
"""
    mako_parameters = ["alInvalidInputMessage"]
    # No server-side validation. The field just tries to help users avoid their own errors.
    # If you want to discuss that decision, make an issue on the repository.
