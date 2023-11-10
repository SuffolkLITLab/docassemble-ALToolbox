$(document).on('daPageLoad', function(){
  /** When the page first loads, gets the value from any `.al_international_phone` input
  *    field, transforms it, puts the transformed value back into the input
  *    field, and adds a dropdown from which to choose a country. It
  *    can also automatically identify the country based on the phone number
  *    if one already exists, for example when a user hits 'Back' to such a page.
  *    When you use it with the docassemble custom datatype for phone numbers
  *    that we've included in the ALToolbox, it will also validate the phone
  *    number when the user taps to continue. The default country is 'us' for
  *    now.
  *
  * This feature uses the library at https://www.npmjs.com/package/intl-tel-input.
  *
  * See phone_number_validation_demo.yml in this library for how to use this
  *    feature of ALToolbox.
  *
  * We have discussed AsYouType input formatter, but haven't approached it yet.
  *    Before discussing it, first see https://github.com/jackocnr/intl-tel-input/issues/346
  *    where int-tel-input decided to get rid of their own version of auto
  *    formatting user input and explained why. It's unclear if it's even possible.
  *    One library to look into is https://nosir.github.io/cleave.js/. It's old,
  *    but we might be able to use it as a model. We would want to test it
  *    extensively with all the pitfalls that int-tel-input brings up and the
  *    issues in the cleave repository itself.
  *
  * More Resources
  *    1. What we're using: https://github.com/jackocnr/intl-tel-input
  *    1. It uses https://www.npmjs.com/package/google-libphonenumber
  *    1. https://github.com/google/libphonenumber/blob/master/FALSEHOODS.md
  *    1. https://github.com/google/libphonenumber/blob/master/FAQ.md
  */
  
  // Loop through all the .al_international_phone input fields on the current screen
  let phoneNodes = document.querySelectorAll( '.al_international_phone' );  // Class given by the CustomDataType
  for ( var node of phoneNodes ) {
    var telObj = window.intlTelInput( node, {
      // The default country without any input into the plugin is 'us'
      // Once the user puts in the phone number of another country, though,
      // it will remember that country
      initialCountry: 'us',
      utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.15/js/utils.min.js",
      autoPlaceholder: "off",
    });
    
    // If the user already entered a number and comes back to the page,
    // docassemble puts the previously saved value into the input field.
    // Unfortunately, docassemble reformats the number and intl-tel-input
    // thinks the number is invalid. It's complicated to describe, but you
    // can see it if you go forward and back three times on our demo screens.
    
    // See https://www.npmjs.com/package/intl-tel-input#recommended-usage about the full international format.
    $(node).val(telObj.getNumber());
  };
  
}); 
