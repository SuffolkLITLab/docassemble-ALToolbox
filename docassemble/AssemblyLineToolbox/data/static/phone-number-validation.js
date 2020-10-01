/* Immediate (client side) jQuery validation of phone number
*  input with options of countries.
*
*  Haven't found a way to get a phone number's country into
*  persistent data.
*
*  # Resources
*  1. What we're using: https://github.com/jackocnr/intl-tel-input
*  1. Especially see: https://github.com/jackocnr/intl-tel-input#static-methods getInstance
*  1. https://www.npmjs.com/package/google-libphonenumber
*  1. https://github.com/google/libphonenumber/blob/master/FALSEHOODS.md
*  1. source: https://www.sitepoint.com/working-phone-numbers-javascript/
*/
$(document).on('daPageLoad', function(){
  // These are always new nodes, even when you click back.
  let phoneNodes = document.querySelectorAll( '.dal-phone' );

  for ( let node of phoneNodes ) {
    let telObj = window.intlTelInput( node, {
      initialCountry: 'US',  // Sorry everyone else :(
      utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.3/js/utils.min.js"
    });
  }
});
