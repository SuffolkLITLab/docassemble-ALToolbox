var al_fade_speed = 300;

function after_click() {
  var thumbs_stage = document.getElementsByClassName('al-thumbs-widget');
  var feedback_stage = document.getElementsByClassName('al-feedback-text');

  for (let elem of thumbs_stage) {
    $(elem).fadeOut(al_fade_speed);
  }
  setTimeout(function() {
    for (let new_elem of feedback_stage) {
      $(new_elem).fadeIn(al_fade_speed);
    }
  }, al_fade_speed);
}

function after_send() {
  var feedback_stage = document.getElementsByClassName('al-feedback-text');
  var all_done_stage = document.getElementsByClassName('al-post-feedback');

  for (let elem of feedback_stage) {
    $(elem).fadeOut(al_fade_speed);
  }
  setTimeout(function() {
    for (let new_elem of all_done_stage) {
      $(new_elem).fadeIn(al_fade_speed);
    }
  }, al_fade_speed);
}

function altoolbox_thumbs_up_send(event_name, has_feedback) {
  action_call(event_name);
  after_click();
  if (!has_feedback) {
    after_send();
  }
}

function altoolbox_thumbs_down_send(event_name, has_feedback) {
  action_call(event_name);
  after_click();
  if (!has_feedback) {
    after_send();
  }
}

function altoolbox_feedback_send(event_name, textarea_id) {
  var feedback_elem = $('#' + textarea_id);
  if (feedback_elem.length > 0) {
    var feedback_text = feedback_elem[0].value;
    action_call(event_name, {feedback_text:feedback_text});
    after_send();
  } else {
    console.log(`Not sending feedback: No element with id ${ textarea_id } on the screen`);
  }
}