$(document).on('daPageLoad', function(){  
  //1. Processing text fields 
  $('input[type="textC"]').each(function(){
	  var inputElement = this;    
    $(inputElement).attr('type', 'text'); // inherit validation.    
	  AddCounterMsg(this);        
  });
  
  //2. Processing textarea fields     
  $('input[type="areaC"]').each(function(){       
    var inputElement = this;        
    var inputID = $(inputElement).attr('id');          
    var content = $(inputElement).val();  
    //Switch to textarea UI    
    var inputBox = $('<textarea class="form-control" alt="input box" rows="4" id="' + inputID + '" name="' + inputID + '">' + content + '</textarea>"');                 
    $(inputElement).replaceWith(inputBox);    
    AddCounterMsg($(inputBox));    
  });  
  
  //3. Processing counter message
  function AddCounterMsg(elm) {
    //Append a message div to input    
    var countMsg = $('<div class="message" style="color: gray; padding-top: 4px"></div>');  
    $(elm).after(countMsg);	 
        
    //Watch input and update the counter message accordingly
	  function updateCount() {			
      var count = $(elm).val().length;   
      if (count == 1) {
        countMsg.text("You have entered " + count + " character.");	                
      } else {
        countMsg.text("You have entered " + count + " characters.");
      }
    }         
    $(elm).on('keyup keydown', updateCount);  
  }
});