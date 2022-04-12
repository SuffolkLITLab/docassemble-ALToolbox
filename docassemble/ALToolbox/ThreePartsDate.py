from docassemble.base.util import CustomDataType, DAValidationError, word, as_datetime, today

js_text = """\
  //this is an adaptation of Jonathan Pyle's datereplace.js
  $(document).on('daPageLoad', function(){
    $('input[type="ThreePartsDate"]').each(function(){
  	  var dateElement = this;
  	  $(dateElement).hide();
  	  $(dateElement).attr('type', 'hidden');
      
      //Construct the input components
  	  var parentElement = $('<div class="form-row row">');	  
  	  var monthParent = $('<div class="col">');
      var monthLabel = $('<div style="text-align:center">Month</div>');	    
      var monthElement = $('<select class="form-control" style="width:7.5em" required>');
  	  var dayParent = $('<div class="col">');    
      var dayLabel = $('<div style="text-align:center">Day</div>');    
      var dayElement = $('<input type="text" class="form-control" type="number" min="1" max="31"  required>' );  
      var yearParent = $('<div class="col">');	  
      var yearLabel = $('<div style="text-align:center">Year</div>');
      //Do not restrict year input range for now. 
      var yearElement = $('<input type="text" class="form-control" type="number" required>');
  	    
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
          
      // Create contents of visible input fields	  
      // "No month selected" option
  	  var opt = $("<option>");
  	  opt.val("");
  	  opt.text("    ");
  	  monthElement.append(opt);
      // Add every calendar month (based on user's computer's date system? lanugage?)
  	  for(var month=0; month < 12; month++){
  	      opt = $("<option>");
  	      if (month < 9){
  	  	opt.val('0' + (month + 1));
  	      }
  	      else{
  	  	opt.val(month + 1);
  	      }
  	      var dt = new Date(1970, month, 1);
  	      opt.text(dt.toLocaleString('default', { month: 'long' }));
          // Use previous values if possible
          if ( dateParts && parseInt( opt.val()) == dateParts[ 0 ]) {
            opt.attr('selected', 'selected');
          }
  	      monthElement.append(opt);
  	  }
    
      // Use previous values if possible
  	  if ( dateParts ) {		
  	  	dayElement.val( dateParts[ 1 ]);
  	  	yearElement.val( dateParts[ 2 ]);
  	  }
      
      //Update original element
  	  function updateDate(){
  	  	$(dateElement).val($(monthElement).val() + '/' + $(dayElement).val() + '/' + $(yearElement).val());	
  	  }	
  	  
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
  	  
  	  yearElement.on('change', updateDate);
  	  monthElement.on('change', updateDate);
  	  dayElement.on('change', updateDate);	
  	  updateDate();
    });
  });  
  $.validator.addMethod('ThreePartsDate', function(value, element, params){
    //Placeholder. Will add client side validation here down the road.
    return /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(value);  
  });
"""

class ThreePartsDate(CustomDataType):
  container_class = 'da-ThreePartsDate-container'
  name = 'ThreePartsDate'
  input_type = 'ThreePartsDate'
  input_class = 'da-ThreePartsDate'
  is_object = True
  javascript = js_text
  jq_rule = 'ThreePartsDate'
  jq_message = 'Your input does not look right.'
  @classmethod
  def validate(cls, item):
	  # Change input string into DADateTime		
    try:
      mydate = as_datetime( item )    
      return True		
    except:
      msg =  item + " is not a valid date."      
      raise DAValidationError(msg)
  
  @classmethod
  def transform(cls, item):
    return as_datetime(item)
  
  @classmethod
  def default_for(cls, item):
    return item.format("MM/dd/yyyy")
  
class BirthDate(ThreePartsDate):
  name = 'BirthDate'
  input_type = 'BirthDate'
  input_class = 'da-BirthDate'
  is_object = True
  jq_rule = 'BirthDate'
  
  javascript = js_text.replace("ThreePartsDate","BirthDate")
  
  @classmethod
  def validate(cls, item):
	  # Change input string into DADateTime		
    try:
      mydate = as_datetime( item )      
    except:
      msg =  item + " is not a valid date."      
      raise DAValidationError(msg)    
    if mydate <= today():
      return True
    else:
      raise DAValidationError("Please enter a date before today")