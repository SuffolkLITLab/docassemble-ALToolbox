$(document).on('daPageLoad', function(){
  // Retrieve country code from a hidden field 
  var country = $(".question-invisible");   
  var country_code = country.val();  
  
  // Set 'us' as the default if country_code has no value.
  if (!country_code){
     country_code = 'us'; 
  }
  // Loop thru all the phone input fields on the current screen
  let phoneNodes = document.querySelectorAll( '.al-intl-phone' );  
  for ( let node of phoneNodes ) {
    let telObj = window.intlTelInput( node, {
      initialCountry: country_code,        
      utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.3/js/utils.min.js"
    });        
    
    // Save input as full number (eg +17024181234) to the backend        
    $(node).val(telObj.getNumber());	

    // Save country input text form (as opposed to digit) separately to the hidden field
    // This value is "undefined" for US numbers, but our default value takes care of that.
    $(country).val(telObj.getSelectedCountryData().iso2);      
  };
  
}); 