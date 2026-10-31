/** intl-tel-input's interface text, in the interview's language. */
function phoneInputTranslations() {
  return {
    ...phoneCountryNames(),
    selectedCountryAriaLabel: alTranslate("Change country, selected ${countryName} (${dialCode})"),
    noCountrySelected: alTranslate("Select country"),
    countryListAriaLabel: alTranslate("List of countries"),
    searchPlaceholder: alTranslate("Search"),
    clearSearchAriaLabel: alTranslate("Clear search"),
    zeroSearchResults: alTranslate("No results found"),
    oneSearchResult: alTranslate("1 result found"),
    multipleSearchResults: alTranslate("${count} results found"),
  };
}

/** Country names come from the browser, which already knows them in every language. */
function phoneCountryNames() {
  const names = {};
  try {
    const regions = new Intl.DisplayNames([alTranslate.language.replace(/_/g, '-')], { type: 'region' });
    for (const country of window.intlTelInput.getCountryData()) {
      names[country.iso2] = regions.of(country.iso2.toUpperCase());
    }
  } catch (error) {
    // Unsupported browser or language: intl-tel-input falls back to English names.
  }
  return names;
}

function setupPhoneInputs() {
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
  const i18n = phoneInputTranslations();
  for ( var node of phoneNodes ) {
    // Rebuilding an input that is already set up replaces its interface text,
    // keeping the country, text and focus the user had
    const previous = window.intlTelInput.getInstance( node );
    const previousCountry = previous?.getSelectedCountryData().iso2;
    const typed = node.value;
    const hadFocus = document.activeElement === node;
    previous?.destroy();
    var telObj = window.intlTelInput( node, {
      // The default country without any input into the plugin is 'us'
      // Once the user puts in the phone number of another country, though,
      // it will remember that country
      initialCountry: previousCountry || 'us',
      i18n,
      loadUtils: () => import("https://cdn.jsdelivr.net/npm/intl-tel-input@25.12.5/build/js/utils.js"),
      autoPlaceholder: "off",
      formatAsYouType: false,
      // Avoid default of MOBILE (https://github.com/jackocnr/intl-tel-input?tab=readme-ov-file#:~:text=validationNumberTypes,-Type%3A%20String)
      validationNumberTypes: null,
    });
    
    // If the user already entered a number and comes back to the page,
    // docassemble puts the previously saved value into the input field.
    // Unfortunately, docassemble reformats the number and intl-tel-input
    // thinks the number is invalid. It's complicated to describe, but you
    // can see it if you go forward and back three times on our demo screens.
    
    // See https://www.npmjs.com/package/intl-tel-input#recommended-usage about the full international format.
    // Only on first setup: intl-tel-input reformats the existing value when it
    // starts, so a rebuild puts back exactly what the user typed.
    if ( previous ) {
      node.value = typed;
      if ( hadFocus ) node.focus();
    } else {
      $(node).val(telObj.getNumber());
    }
  };
}

$(document).on('daPageLoad', setupPhoneInputs);
// On the first visit in a language the translations arrive after the page is drawn
window.addEventListener('alTranslationsLoaded', setupPhoneInputs);

