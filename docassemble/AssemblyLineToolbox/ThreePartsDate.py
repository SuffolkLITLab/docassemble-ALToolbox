from docassemble.base.util import CustomDataType, DAValidationError, word, as_datetime

class textdate(CustomDataType):
  container_class = 'da-ThreePartsDate-container'
  name = 'ThreePartsDate'
  input_type = 'ThreePartsDate'
  input_class = 'da-ThreePartsDate'
  javascript = """\
  $.validator.addMethod('ThreePartsDate', function(value, element, params){
    //Placeholder. Will add client side validation here down the road.
    return /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(value);  
  });
"""
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
		