// Keep the escape button visible in the nav bar, even when the screen gets small
$(document).on('daPageLoad', function(){

  // Our button
  let button = $( '.al_escape_nav' );
  // The docassemble collapsing nav bar menu
  let sibling = $( '#damobile-toggler' );
  // Turn the button into a sibling of the nav bar menu instead of its child
  button.insertBefore( sibling );

});  // Ends on daPageLoad
