$(document).on('daPageLoad', function () {
  try {
    var copy_nodes = document.getElementsByClassName('al_copy');

    function copyText( text ) {
      if ( navigator.clipboard && navigator.clipboard.writeText ) {
        return navigator.clipboard.writeText( text );
      }

      return new Promise(function( resolve, reject ) {
        try {
          var temp_input = document.createElement('textarea');
          temp_input.value = text;
          temp_input.setAttribute('readonly', '');
          temp_input.style.position = 'absolute';
          temp_input.style.left = '-9999px';
          document.body.appendChild( temp_input );
          temp_input.select();
          document.execCommand('copy');
          document.body.removeChild( temp_input );
          resolve();
        } catch ( error ) {
          reject( error );
        }
      });
    }

    for ( var node_i = 0; node_i < copy_nodes.length; node_i++ ) {
      add_copy_event_listeners( $(copy_nodes[ node_i ]) );
    }

    function add_copy_event_listeners( $node ) {
      var copy_value = $node.find('.al_copy_value')[0];
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
          var text_to_copy = copy_value.value || copy_value.textContent || '';

          copyText( text_to_copy ).then(function() {
            $tooltip_inert.hide()
            $tooltip_active.show()
          }).catch(function( error ) {
            console.warn( 'Error in AL copy button click' );
            console.warn( error );
          });

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
