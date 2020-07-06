//this is a revision of Jonathan Pyle's datereplace.js
$(document).on('daPageLoad', function(){
    $('input[type="textdate"]').each(function(){
	var dateElement = this;
	$(dateElement).hide();
	$(dateElement).attr('type', 'hidden');
	var parentElement = $('<div class="form-row">');
	var yearParent = $('<div class="col">');
	var monthParent = $('<div class="col">');
	var dayParent = $('<div class="col">');
	
	var yearLabel = $('<div style="text-align:center">Year</div>');
	var dayLabel = $('<div style="text-align:center">Day</div>');
	var monthLabel = $('<div style="text-align:center">Month</div>');	
	var yearElement = $('<input type="text" class="form-control" type="number" min="1901" max="2020" required>');
	var dayElement = $('<input type="text" class="form-control" type="number" min="1" max="31"  required>' );
	var monthElement = $('<select class="form-control" style="width:7.5em" required>');
		
	var dateEntered;	
	if ($(dateElement).val()){
	    var utcDate = new Date($(dateElement).val());
	    dateEntered = new Date(utcDate.getUTCFullYear(), utcDate.getUTCMonth(), utcDate.getUTCDate());
	}
	else{
	    dateEntered = null;
	}
	
	var opt = $("<option>");
	opt.val("");
	opt.text("    ");
	monthElement.append(opt);
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
	    if (dateEntered && month == dateEntered.getMonth()){
		opt.attr('selected', 'selected');
	    }
	    monthElement.append(opt);
	}
	if (dateEntered) {		
		dayElement.attr('value', dateEntered.getDate());
		yearElement.attr('value', dateEntered.getFullYear());
	}
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