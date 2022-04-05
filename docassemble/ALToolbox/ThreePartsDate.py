from docassemble.base.util import (
    CustomDataType,
    DAValidationError,
    word,
    as_datetime,
    today,
    date_difference,
    log,
)
import re

js_text = """\
  //this is an adaptation of Jonathan Pyle's datereplace.js
  $(document).on('daPageLoad', function(){
    $('input[type="ThreePartsDate"]').each(function(){
      var dateElement = this;
      var required = $(dateElement).closest('.da-form-group').hasClass('darequired');
      $(dateElement).hide();
      $(dateElement).attr('type', 'hidden');
      $(dateElement).attr('aria-hidden', 'true');
      
      //Construct the input components
      var parentElement = $('<div class="form-row row">');
      
      var monthParent = $('<div class="col">');
      var monthLabel = $('<div style="text-align:center">Month</div>');     
      var monthElement = $('<select class="form-control" style="width:7.5em">');
      monthElement.attr( 'required', required );
      monthElement.prop( 'required', required );
      
      var dayParent = $('<div class="col">');    
      var dayLabel = $('<div style="text-align:center">Day</div>');    
      var dayElement = $('<input type="text" class="form-control" type="number" min="1" max="31">' );
      dayElement.attr( 'required', required );
      dayElement.prop( 'required', required );
      
      var yearParent = $('<div class="col">');    
      var yearLabel = $('<div style="text-align:center">Year</div>');
      //Do not restrict year input range for now. 
      var yearElement = $('<input type="text" class="form-control" type="number">');
      yearElement.attr( 'required', required );
      yearElement.prop( 'required', required );
        
      // If we're returning to a variable that has already been defined
      // prepare to use that variable's values
      var dateParts;
      if ( $(dateElement).val() ) {
        dateParts = $(dateElement).val().split( '/' );
        dateParts.forEach( function( part, index, dateParts ) {
          dateParts[ index ] = parseInt( part );
        });
      } else {
        dateParts = null;
      }
          
      // Insert previous answers if possible
      
      // -- Month --
      // "No month selected" option
      var first_opt = $("<option>");
      first_opt.val("");
      first_opt.text("");
      monthElement.append( first_opt );
      // Add every calendar month (based on user's computer's date system? lanugage?)
      var option = null
      for(var month=0; month < 12; month++){
        opt = $("<option>");
        if ( month < 9 ){
          opt.val('0' + (month + 1));
        } else {
          opt.val(month + 1);
        }
        
        // Convert the month number to a month name for the option text
        var dt = new Date(1970, month, 1);
        opt.text(dt.toLocaleString('default', { month: 'long' }));
        
        // Use previous values if possible
        if ( dateParts && parseInt( opt.val() ) === dateParts[ 0 ]) {
          opt.attr('selected', 'selected');
        }
        
        monthElement.append(opt);
      }  // ends for every month
    
      // -- Day and year --
      // Use previous values if possible
      if ( dateParts ) {    
        dayElement.val( dateParts[ 1 ]);
        yearElement.val( dateParts[ 2 ]);
      }
      
      // Update value of original input when changes values.
      function updateDate(){
        var val = $(monthElement).val() + '/' + $(dayElement).val() + '/' + $(yearElement).val();
        if ( val === '//' ) { val = ''; }
        $( dateElement ).val( val );
      };  // Ends updateDate()
      
      $(dateElement).before(parentElement); 
      $(monthParent).append(monthLabel);
      $(monthParent).append(monthElement);
      $(parentElement).append(monthParent); 
      $(dayParent).append(dayLabel);
      $(dayParent).append(dayElement);
      $(parentElement).append(dayParent); 
      $(yearParent).append(yearLabel);
      $(yearParent).append(yearElement);
      $(parentElement).append(yearParent);
      
      // Updates will be triggered when the user leave an input field
      yearElement.on('change', updateDate);
      monthElement.on('change', updateDate);
      dayElement.on('change', updateDate);
    });
  });
  
  // No jQuery validation, since it doesn't work on hidden elements
"""


class ThreePartsDate(CustomDataType):
    name = "ThreePartsDate"
    input_type = "ThreePartsDate"
    javascript = js_text
    jq_message = word("Answer with a valid date")
    is_object = True
    # Probably won't work because the input to validate is hidden
    jq_rule = "date"

    @classmethod
    def validate(cls, item):
        # If there's no input in the item, it's valid
        if not isinstance(item, str) or item == "":
            return True
        else:
            # Otherwise it needs to be a date after the year 1000. We ourselves make
            # sure this format is created if the user gives valid info.
            matches_date_pattern = re.search(r"^\d{1,2}\/\d{1,2}\/\d{4}$", item)
            if matches_date_pattern:
                try:
                    date = as_datetime(item)
                except Exception as error:
                    msg = f"{ item } {word('is not a valid date')}"
                    raise DAValidationError(msg)

                return True
            else:
                raise DAValidationError(f"{ item } {word('is not a valid date')}")

    @classmethod
    def transform(cls, item):
        if item:
            return as_datetime(item)

    @classmethod
    def default_for(cls, item):
        if item:
            return item.format("MM/dd/yyyy")


class BirthDate(ThreePartsDate):
    name = "BirthDate"
    input_type = "BirthDate"
    javascript = js_text.replace("ThreePartsDate", "BirthDate")
    jq_message = word("Answer with a valid date of birth")
    is_object = True
    # Probably won't work because the input to validate is hidden
    jq_rule = "date"

    @classmethod
    def validate(cls, item):
        # If there's no input in the item, it's valid
        if not isinstance(item, str) or item == "":
            return True
        else:
            # Otherwise it needs to be a date on or before today and after the year 1000.
            # We ourselves create this format if the user gives valid info.
            matches_date_pattern = re.search(r"^\d{1,2}\/\d{1,2}\/\d{4}$", item)
            try:
                date = as_datetime(item)
            except Exception as error:
                msg = f"{ item } {word('is not a valid date')}"
                raise DAValidationError(msg)
            if matches_date_pattern:
                date_diff = date_difference(starting=date, ending=today())
                if date_diff.days >= 0.0:
                    return True
                else:
                    raise DAValidationError(
                        word("Answer with a <strong>date of birth</strong>")
                    )
            else:
                msg = (
                    f"{ item } {word('is not a valid <strong>date of birth</strong>')}"
                )
                raise DAValidationError(msg)
