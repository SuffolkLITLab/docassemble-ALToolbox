$(document).on('daPageLoad', function () {
  try {
    var copy_nodes = document.getElementsByClassName('al_copy');

    for ( var node_i = 0; node_i < copy_nodes.length; node_i++ ) {
      add_copy_event_listeners( $(copy_nodes[ node_i ]) );
    }

    function add_copy_event_listeners( $node ) {
      var input = $node.find('.al_copy_value')[0];
      var $button = $node.find('.al_copy_button').eq(0);
      var $tooltip_inert = $node.find('.al_tooltip_inert').eq(0);
      var $tooltip_active = $node.find('.al_tooltip_active').eq(0);

      $button.on( 'mouseenter', function ( event ) {
        try {
          $tooltip_inert.show()
          $tooltip_active.hide()

        } catch ( error ) {
          console.warn( 'Error in AL copy button mouseenter' );
          console.warn( error );
        }
      });

      $button.on( 'click', function ( event ) {
        try {
          input.focus();
          input.select();
          document.execCommand("copy");

          $tooltip_inert.hide()
          $tooltip_active.show()
          input.blur();

        } catch ( error ) {
          console.warn( 'Error in AL copy button click' );
          console.warn( error );
        }
      });

      $button.on( 'mouseleave', function ( event ) {
        try {
          $tooltip_inert.hide()
          $tooltip_active.hide()

        } catch ( error ) {
          console.warn( 'Error in AL copy button mouseleave' );
          console.warn( error );
        }
      });
    }
  } catch ( error ) {
    console.warn( 'Error in AL copy button instantiation');
    console.warn( error );
  }
})
