from docassemble.base.util import (
    CustomDataType,
    DAValidationError,
    word,
    as_datetime,
    today,
    date_difference,
    log,
)
from typing import Optional
import re

__all__ = ["ThreePartsDate", "BirthDate"]

js_text = """\
// This is an adaptation of Jonathan Pyle's datereplace.js

/*
* Notes to keep around:
* - Rule names must avoid dashes and underscores because of plugin and da limitations.
* - Avoid a min date default for birthdays. Too hard to predict developer needs, like great-grandmother's birthday. Document that developers need to set a min value if they want one.
* - Cannot use regular `min`/`max` attributes. We can get that the rules exist, but we can't get their messages.
* - Notes on js date inconsistencies: https://dygraphs.com/date-formats.html
* 
* TODO: (post MVP)
* - Get the 'Month'/'Day'/'Year' word values as mako_parameters too so they can be translated. Same as we do within the message functions.
* - Deal with international user date input and international dev date attributes.
* - Handle non-US formatted dates.
* - Consider decreasing padding-right of the day and year fields as sometimes extra numbers get hidden. e.g. A day of 331 only shows the 33. Maybe remove the padding completely to make sure it's clear the text has gone past the edge.
*
* Post MVP validation priority (https://design-system.service.gov.uk/components/date-input/#error-messages):
*  1. missing or incomplete information (when parent is no longer in focus, highlight fields missing info?)
*  2. information that cannot be correct (for example, the number ‘13’ in the month field, 3-digit year)
*  3. information that fails validation for another reason
* Or validate from left to right
*
* Bugs:
* Bad things happen when a user submits invalid fields (upstream?). Note that no other invalidation highlighting appears. If any, it's only our new stuff:
* - Required:
*   - (partly solved by `add_to_groups()` - outline is restored after new on-page error) Any on-page invalid message(s) with any fields filled, message will lose the outline, but only have 1 message. Thereafter, the outline for on-page invalidation will appear, but won't contain the error message.
*   - Required fields with default values don't get invalidated when they are first emptied. They have to have a value put in them and then that value removed. (Upstream?)
* - Sometimes after submission, one validation message will be inside the outline and another outside it. This needs to be replicated consistently to see if `add_to_groups()` can solve this. (upstream?)
* - When one non-required field is empty on submission and there is no on-page invalidation error, the error appears with no red outline. After that, getting a non-submission invalidation message will show the red outline, but the error will be outside of it. Not solved by `add_to_groups()`.
* - Note: At the very least, when submitting before getting a three parts date on-page validation message, our custom errorPlacement doesn't run. There may be other times too. Maybe try moving any existing error on daPageLoad, though not sure this runs after form submission. (Upstream?)
* - Missing error messages: Submit validation only shows an error for one three parts date, even if there are multiple fields on the page. This is a preexisting bug. (Upstream?)
*/

// da doesn't log the full error sometimes, so we'll do our own try/catch
try {{

$(document).on('daPageLoad', function(){{
  $('input[type="ThreePartsDate"]').each(function(){{
    let $al_date = replace_date(this);
    set_up_validation($al_date);
  }});  // ends for each date datatype
}});  // ends on da page load
  
  
function replace_date(original_date) {{
  /** Replace the original date element with our 3 fields and
  *   make sure the fields update the original date value.
  * 
  * @param {{HTML Node}} date The original date element.
  * 
  * @returns {{jQuery obj}} AL container for all the three parts date elements
  */
  let $original_date = $(original_date);
  $original_date.hide();
  $original_date.attr('type', 'hidden');
  $original_date.attr('aria-hidden', 'true');
  
  var $al_date = $('<div class="al_three_parts_date form-row row">');
  $original_date.before($al_date);

  var date_id = $original_date.attr('id');
  
  // -- Construct the input components --
  let $month = create_month(date_id);
  let $day = create_date_part({{date_id, type: 'day'}});
  let $year = create_date_part({{date_id, type: 'year'}});
      
  // -- Add them to the DOM --
  $al_date.append($month.closest('.col'));
  $al_date.append($day.closest('.col'));
  $al_date.append($year.closest('.col'));
  add_error_container($al_date);
  
  // --- Use other original date features ---
  // Avoid .data() for our dynamic stuff - caching problems
  // https://forum.jquery.com/topic/jquery-data-caching-of-data-attributes
  // https://stackoverflow.com/a/8708345/14144258
  
  // Also, original field gets disabled by da on load. Our fields are added
  // after that, so da can't affect them. Must do these attrs ourselves.
  if (is_required($al_date)) {{
    $year.attr('required', true);
    $month.attr('required', true);
    $day.attr('required', true);
  }}
  
  if ($original_date[0].disabled) {{
    $month.attr('disabled', true);
    $day.attr('disabled', true);
    $year.attr('disabled', true);
  }}
  
  use_previous_values({{$original_date, $al_date}});
  
  // Ensure original date field is updated when needed so that
  // submitting the form sends the right data.
  // Updates will be triggered when the user leaves an input field.
  $year.on('change', update);
  $month.on('change', update);
  $day.on('change', update);
  function update() {{
    update_original_date($al_date);
  }};
  
  return $al_date;
}};  // Ends replace_date()
  

function create_date_part({{type, date_id}}) {{
  /** Return one date part with a label and input inside a container.
  *   TODO: Should we use the original dates's `name` instead of `id`?
  *   They've been the same so far. Will they always be?
  * 
  * @param {{str}} type 'year' or 'day'
  * @param {{str}} date_id ID of the original date field
  * 
  * @returns undefined
  */
  var $col = $('<div class="col col-3 col-' + type + '">');
  var id = '_ignore_' + date_id + '_' + type;
  // '_ignore' in the name prevents the field from being submitted, avoiding a da error
  let name = id;
  
  // For python formatting, need to have {{day}} and {{year}}
  let $label = '';
  if (type === 'day') {{
    $label = $('<label for="' + id + '">{day}</label>');
  }} else {{
    $label = $('<label for="' + id + '">{year}</label>');
  }}
  $col.append($label);
  
  // Reconsider type `number`, `inputmode` ("numeric") not fully supported yet
  // (02/09/2023). When it is, change to `type='text'`. Also, when we _do_ remove
  // `type='number'` also add a check in invalid day check to see if either the
  // year or day is not a number. See warning in that function.
  // Avoid attr `pattern` - voice control will enter invalid input:
  // https://github.com/alphagov/govuk-design-system-backlog/issues/42#issuecomment-775103437
  
  // aria-describedby is ok to have, even when the date-part error is
  // not present or is display: none
  var $field = $('<input class="form-control al_field ' + type + ' ' + date_id + '" type="number" min="1" inputmode="numeric">');
  $field.attr('id', id);
  $field.attr('name', name);
  // There's only one message element, so all fields are described by it.
  // Not sure how the validation plugin associates the original input's id with this.
  $field.attr('aria-describedby', date_id + '-error');
  $col.append($field);
  
  return $field;
}};  // Ends create_date_part()

  
function create_month(date_id) {{
  /** Return one month type date part given the original date node id.
  *   TODO: Should we use the original dates's `name` instead of `id`?
  *   They've been the same so far. Will they always be?
  * 
  * @param {{str}} date_id ID of the original date field
  * 
  * @returns undefined
  */
  var $col = $('<div class="col col-month">');
  
  let id = '_ignore_' + date_id + '_month';
  // '_ignore' in the name prevents the field from being submitted, avoiding a da error
  let name =  id;
  
  let $label = $('<label for="' + id + '">{month}</label>');
  $col.append($label);
  
  // aria-describedby is ok to have, even when the date-part error is
  // not present or is display: none
  // `for` is label of field while `aria-describedby` is supplemental info
  // https://developer.mozilla.org/en-US/docs/Web/CSS/display#display_none
  // https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-hidden
  
  // There's only one message element, so all fields are described by it.
  // Not sure how the validation plugin associates the original input's id with this.
  var $field = $('<select class="form-select al_field month ' + date_id + '">');
  $field.attr('id', id);
  $field.attr('name', name);
  // There's only one message element, so all fields are described by it
  $field.attr('aria-describedby', date_id + '-error');
  add_month_options($field);
  
  $col.append($field);
  
  return $field;
}};  // Ends create_month()


function add_month_options(select) {{
  /** Add month values to selection field.
  * 
  * @param {{HTML Node | $ obj}} select A <select> node.
  * 
  * @returns undefined
  */
  let $select = $(select);
  
  // "No month selected" option.
  // TODO: Should this have text for accessibility?
  let $blank_opt = $('<option value=""></option>');
  $select.append( $blank_opt );
  
  // Add every calendar month (based on user's computer's date system? lanugage?)
  for(var month=0; month < 12; month++) {{
    let $opt = $("<option>");
    $opt.val((month + 1 ).toString().padStart(2,0));

    // Convert the month number to a month name for the option text
    var date = new Date(1970, month, 1);
    $opt.text(date.toLocaleString('default', {{ month: 'long' }}));

    $select.append($opt);
  }}  // ends for every month
}};  // Ends add_month_options()
  
  
function use_previous_values({{$original_date, $al_date}}) {{
  /** If $original_date has an existing value, set the date fields values to match.
  *   E.g. If we're returning to a variable that has already been defined.
  * 
  * @param {{$ obj}} $original_date jQuery obj of the original date element.
  * @param {{$ obj}} $al_date jQuery obj of the al parent of our three parts date parts.
  * 
  * @returns undefined
  */
  let date_parts;
  if ( $original_date.val() ) {{
    date_parts = $original_date.val().split( '/' );
    // TODO: Take care of dates with a '-' delimeter?
    date_parts.forEach( function( part, index, date_parts ) {{
      let part_int = parseInt( part );
      if (isNaN(part_int)) {{
        date_parts[ index ] = '';
      }} else {{
        date_parts[ index ] = part_int;
      }}
    }});
  }} else {{
    date_parts = null;
  }}
  
  // TODO: Select "" option if month is empty string?
  if (date_parts && date_parts[0]) {{
    // Ensure 1 becomes "01", etc.
    let month_str = date_parts[0].toString().padStart(2,0);
    let $month = $($al_date.find('select.month')[0]);
    $($month.children('option[value="' + month_str + '"]')).prop('selected', true);
  }}
  
  if (date_parts) {{
    $($al_date.find('input.day')[0]).val(date_parts[1]);
    $($al_date.find('input.year')[0]).val(date_parts[2]);
  }}
}};  // Ends use_previous_values()
  
  
function add_error_container($al_date) {{
  /** Add element that will contain all errors.
  * 
  * @param {{$ obj}} $al_date The al parent of our three parts date parts.
  * 
  * @returns undefined
  */
  let $original_date = get_$original_date($al_date);
  let $error = $('<div id="al_' + $original_date.attr('id') + '_error" class="al_error"></div>');
  $al_date.append($error);
  return $error;
}};  // Ends add_error_container()
  

function update_original_date($al_date) {{
  /** Update value in original date field using the values
  *   of the al three parts date parts.
  * 
  * @param {{$ obj}} $original_date The original date element.
  * @param {{$ obj}} $al_date The al parent of our three parts date parts.
  * 
  * @returns undefined
  */
  var data = get_date_data($al_date);
  
  let US_date = data.month + '/' + data.day + '/' + data.year;
  if (US_date === '//') {{
    US_date = '';
  }}
  
  let val_date = US_date;
  
  get_$original_date($al_date).val(val_date);
}};  // Ends update_original_date()
  
  
// ==================================================
// ==================================================
// === Get elements and element data ===
// ==================================================
// ==================================================

function is_required(element) {{
  /*** Returns true if date value is required, otherwise returns false.
  * 
  * @param {{Node}} element AL three parts date element. Can be parent of date parts.
  * 
  * @returns {{bool}}
  */
  let $original_date = get_$original_date(element);
  return $original_date.closest('.da-form-group').hasClass('darequired');;
}}  // Ends is_required()
  
  
function get_date_data(element) {{
  /**
  * Given an element that holds a part of the date information,
  * return the full date data as an object.
  * 
  * @param {{HTML Node | $ obj}} element Any al three parts date element, including parent.
  * 
  * @returns {{year: str, month: str, day: str}}
  */
  var year_elem = get_$al_date(element).find('input.year')[0];
  var month_elem = get_$al_date(element).find('select.month')[0];
  var day_elem = get_$al_date(element).find('input.day')[0];
  var date_data = {{
    year: $(year_elem).val(),
    month: $(month_elem).val(),
    day: $(day_elem).val(),
  }};
  return date_data;
}};  // Ends get_date_data()
  
  
function is_birthdate(element) {{
  /** If the element is part of a al birthdate field, returns true, otherwise false.
  * 
  * @param {{HTML Node}} element Any al three parts date element, including al parent.
  * @returns {{bool}}
  */
  // For actual environment:
  let birthdate = get_$al_date(element).parent().find('.daBirthDate')[0];
  if (!birthdate) {{
    // For development:
    birthdate = get_$al_date(element).parent().find('.daALBirthDateTestValidation2')[0];
  }}
  return Boolean(birthdate);
}};  // Ends is_birthdate()

  
function get_$original_date(element) {{
  /** Returns jQuery obj of original date element or an empty jQuery object.
  * 
  * @param {{HTML Node}} element Any al three parts date element, including al parent.
  * 
  * @returns {{jQuery obj}}
  */
  return $($(element).closest('.dafieldpart').children('input')[0]);
}};  // Ends get_$original_date()
  
  
function get_$al_date(element) {{
  /** Using any element inside the element containing our three parts date,
  *   return the element we created to surround our date elements.
  *   If it doesn't exist, will return an empty jQuery object.
  *   Easier to maintain all in one place. Consider returning
  *   a plain element - calling functs won't have to know how
  *   to check for an empty jQuery object.
  * 
  * @param {{HTML Node}} element Any element.
  * 
  * @returns {{jQuery obj}} Note: can be an "empty" jQuery object.
  */
  // `.closest()` will get the element itself if appropriate
  return $(element).closest('.dafieldpart').find('.al_three_parts_date');
}};  // Ends get_$al_date()
  
  
// ==================================================
// ==================================================
// === Validation ===
// ==================================================
// ==================================================
  
function set_up_validation($al_date) {{
  /** Uses jQuery validation plugin to set up validation functionality
  * 
  * @param {{$ obj}} $al_date jQuery obj of the al parent of our three parts date parts.
  * 
  * @returns undefined
  */
  $al_date.find('.al_field').each(function make_validator_options (index, field) {{
    add_rules(field);
    add_messages(field);
    add_to_groups(field);
  }});
  
  // There's some strange behavior on submission outlined in the
  // description of bugs. This helps with those involving multiple
  // messages cropping up. Avoid adding rules and messages to the
  // original field for now, though. That seemed to cause issues.
  let $original_date = get_$original_date($al_date);
  add_to_groups($original_date);
  
  let validator = $("#daform").data('validator');
  set_up_errorPlacement(validator);
  set_up_highlight(validator);
  set_up_unhighlight(validator);
}};  // Ends set_up_validation()
  

// ==================================================
// ===== Valdiation plugin configs =====
// ==================================================
  
function add_rules(field) {{
  /** Add all date rules to a given field.
  * 
  * @param {{HTML Node}} field An al three parts date field.
  * 
  * @returns undefined
  */
  // The order they are called in is complex to control. One possibility:
  // https://stackoverflow.com/a/5682617
  let rules = {{
    alMin: get_$original_date(field).attr('data-alMin') || false,
    alMax: is_birthdate(field) || get_$original_date(field).attr('data-alMax'),
    _alInvalidDay: true,  // e.g. 1/54/2000 is invalid. TODO: Should devs be able to disable this?
    _alInvalidYear: true,  // e.g. 200 or 012. TODO: Should devs be able to disable this?
    // Normal `required` only deals with one field being empty, not empty siblings
    _alRequired: is_required(field),
  }};  // ends rules
  
  $(field).rules('add', rules);
}};  // Ends add_rules()
  
  
function add_messages(field) {{
  /** Adds custom messages that are in the validator object
  *   and don't need parameters.
  * 
  * @param {{HTML Node}} field An al three parts date field.
  * 
  * @returns undefined
  */
  let messages = $("#daform").data('validator').settings.messages;
  let name = get_$original_date(field).attr('name');
  
  // If there's are custom messages in the validator object, use them
  if (messages[name]) {{
    $(field).rules('add', {{
      messages: {{
        // We can access the original da `required` message
        required: messages[get_$original_date(field).attr('name')].required,
        // Normal `required` only deals with one field being empty, not empty siblings
        _alRequired: messages[get_$original_date(field).attr('name')].required,
      }}
    }});  // ends add rules
  }}  // ends if required message exists
  
}};  // Ends add_messages()
  
  
function add_to_groups(field) {{
  /** Add field to its group dynamically after-the-fact. We have
  *   to do this because da has already created its groups and we
  *   don't want to override anything.
  *   Note: Adding groups dynamically here won't be reflected in `validator.settings`
  * 
  *   Inspired by https://stackoverflow.com/a/9688284/14144258
  * 
  * @param {{HTML Node}} field An al three parts date field.
  * 
  * @returns undefined
  */
  let groups = $("#daform").data('validator').groups;
  groups[ $(field).attr('name') ] = get_$original_date(field).attr('id');
}};  // Ends add_to_groups()
  
  
// ==================================================
// ===== Validation methods =====
// ==================================================
  
// -- Whole date validations --

$.validator.addMethod('alMin', function(value, field, params) {{
  /** Returns true if full date is >= min date or incomplete. */
  if (!date_is_ready_for_min_max(field)) {{
    return true;
  }}
  
  // TODO: Catch invalid `data-alMin` attr values? Useful for devs.
  // Otherwise very hard for devs to track down. Log in console?
  // Non-MVP. Make an issue.
  // Replace '-' in case it's an ISO date format, (our recommended format).
  // JS doesn't play nicely with ISO format.
  let min_attr = get_$original_date(field).attr('data-alMin') || "";
  let min_date = new Date(min_attr.replace(/-/g, '/'));
  if (isNaN(min_date)) {{
    if (min_attr !== "") {{
      console.log(`The alMin attribute (${{ min_attr }}) isn't a valid date!`);
    }}
    // Validation should always succeed if no or bad minimum given
    return true;
  }}
  
  // Avoid using `params`, which could be in many different formats.
  // Just get date data from the actual fields
  var data = get_date_data(field);
  var date_input = new Date(data.year + '/' + data.month + '/' + data.day);
  
  return date_input >= min_date;
  
}}, function alMinMessage (validity, field) {{
  /** Returns the string of the invalidation message, or blank string for
   * safety and consistency with alMaxMessage. */
  let min_attr = get_$original_date(field).attr('data-alMin') || "";
  let min_date = new Date(min_attr.replace(/-/g, '/'));
  let locale_long_date = min_date.toLocaleDateString(undefined, {{ day: '2-digit', month: 'long', year: 'numeric' }});
  return (
    get_$original_date(field).attr('data-alMinMessage')
    || get_$original_date(field).attr('data-alDefaultMessage')
    || `The date needs to be on or after ${{ locale_long_date }}.`
  );
}});  // ends validate 'alMin'
  
  
$.validator.addMethod('alMax', function(value, field, params) {{
  /** Returns true if full date is <= max date or is incomplete. */
  if (!date_is_ready_for_min_max(field)) {{
    return true;
  }}

  // TODO: Catch invalid alMax attr values for devs? Log in console? Make post MVP issue
  let max_attr = get_$original_date(field).attr('data-alMax') || "";
  let max_date = new Date(max_attr.replace(/-/g, '/'));
  if (isNaN(max_date)) {{
    if (max_attr !== "") {{
      console.log(`The alMax attribute (${{ max_attr }}) isn't a valid date!`);
    }}
    if (!is_birthdate(field)) {{
      // Validation should always succeed if no or bad max given on normal dates
      return true;
    }} else {{
      // if birthdate and no or bad max given, assume today is the max date
      max_date = new Date();
    }}
  }}
  
  // Avoid using `params`, which could be in many different formats.
  // Just get date data from the actual fields
  var data = get_date_data(field);
  var date_input = new Date(data.year + '/' + data.month + '/' + data.day);
  
  return date_input <= max_date;
  
}}, function alMaxMessage (validity, field) {{
  /** Returns the string of the invalidation message. */
  let max_attr = get_$original_date(field).attr('data-alMax') || "";
  let max_date = new Date(max_attr.replace(/-/g, '/'));
  let locale_long_datetime = max_date.toLocaleDateString(undefined, {{ day: '2-digit', month: 'long', year: 'numeric' }})
  let default_MaxMessage = `The date needs to be on or before ${{ locale_long_datetime }}.`;
  // Birthdays have a different default max message
  if (is_birthdate(field) && isNaN(max_date)) {{
    default_MaxMessage = 'A <strong>birthdate</strong> must be in the past.';
  }}
  
  return (
    get_$original_date(field).attr('data-alMaxMessage')
    || get_$original_date(field).attr('data-alDefaultMessage')
    || default_MaxMessage
  );
}});  // ends validate 'alMax'
  
  
// --- Validate individual fields ---
// Always check each others' field any time any field is validated. That
// way one valid field can't take away the message/highlighting for another
// invalid field.
  
$.validator.addMethod('_alInvalidDay', function(value, field, params) {{
  /** Returns false if full input values cannot be converted to a
  *   matching Date object. E.g. HTML won't recognize 12/32/2000 as an
  *   invalid date. It will instead convert it to 1/1/2001.
  *   Only day inputs can create mismatching dates, but this must be
  *   checked whenever any field is updated. If the user puts Jan 30 and
  *   then change month to Feb, we need to show the error then. If the
  *   user puts 2/29/2020 and changes to 2021, that must be shown too.
  */
  // Doesn't need to be abstracted anymore in some ways, but it does
  // make this addMethod section of the code cleaner.
  return has_valid_day(field);
}}, function alInvalidDayMessage (validity, field) {{
  /** Returns the string of the invalidation message. */
  
  // Always return a custom message first
  let custom_msg = get_$original_date(field).attr('data-alInvalidDayMessage')
                   || get_$original_date(field).attr('data-alDefaultMessage');
  if (custom_msg) {{
    return custom_msg;
  }}
  
  let input_date = get_$al_date(field).find('.day').val();
  
  // If the date is only partly filled, we can't give a useful message
  // without a heck of  a lot of work, so give a generalized invalid day
  // default message.
  let data = get_date_data(field);
  if (data.year == '' || data.month == '') {{
    return `No month has ${{input_date}} days.`;
  }}
  
  // Otherwise we can give the full default message
  let input_year = get_$al_date(field).find('.year').val();
  let converted_year = (new Date(input_year, 1, 1)).getFullYear();
  let input_month = get_$al_date(field).find('.month option:selected').text();
  
  return `${{input_month}} ${{converted_year}} doesn't have ${{input_date}} days.`;
}});  // ends validate '_alInvalidDay'
  

$.validator.addMethod('_alInvalidYear', function(value, field, params) {{
  /** Returns true if year is empty or has 4 digits.
  * 
  * @returns {{bool}}
  */
  let text = get_$al_date(field).find('input.year')[0].value;
  // Empty year is not invalid in this way
  if (text.length === 0) {{return true;}}
  // Dates will remove leading 0's, thus sadly 0011 == 2011
  if (text.length !== 4 || text[0] === '0') {{
    return false;
  }} else {{
    return true;
  }}
  
}}, function alInvalidYearMessage (validity, field) {{
  /** Returns the string of the invalidation message. */
  return (
    get_$original_date(field).attr('data-alInvalidYearMessage')
    || get_$original_date(field).attr('data-alDefaultMessage')
    || `The year needs to be 4 digits long and cannot start with "0".`
  );
}});  // ends validate '_alInvalidYear'
  

$.validator.addMethod('_alRequired', function(value, field, params) {{
  /** Returns true if
  *   - original field is hidden/disabled
  *   - all fields have contents
  *   - current field has contents and other fields haven't been interacted with yet
  *   Otherwise returns false.
  *
  * Unable to give a specific message about which date field is missing values
  *   (like in the CustomDataType 'submit' validation messages do) as we'd have
  *   to show a lot of premature error messages.
  * 
  * @returns {{bool}}
  */
  // Remember that this field has been interacted with for validation.
  $(field).addClass('al_dirty');
  
  // For clarity, if the field itself has just been made empty, easy choice
  if ($(field).val() === '') {{
    return false;
  }}
  
  let all_dirty_fields_have_contents = true;
  // For all related three parts date fields
  get_$al_date(field).find('.al_field').each(function (index, a_field) {{
    // If a field has been interacted with by this rule at least once
    if ( $(a_field).hasClass('al_dirty') ) {{
      // and it's now empty
      if ($(a_field).val() === '') {{
        // all fields should be invalid
        all_dirty_fields_have_contents = false;
      }}
    }}
  }});
  
  return all_dirty_fields_have_contents;
}});  // ends validate 'required'
  
  
// ==================================================
// ===== Validation calculations =====
// ==================================================

function date_is_ready_for_min_max(element) {{
  /** Return true if date input is ready to be evaluated for min/max
  *   date value invalidation.
  * 
  * @param {{HTML Node}} element Any al three parts date element, including the parent.
  * 
  * @returns {{bool}}
  */
  var data = get_date_data(element);
  // Don't evaluate min/max if the date is only partly filled
  if (data.year == '' || data.month == '' || data.day === '') {{
    return false;
  }}
  // If the date is invalid in another way, we shouldn't have been able to
  // get in here, but just in case.
  let date_val = new Date(data.year + '/' + data.month + '/' + data.day);
  if (isNaN(date_val)) {{
    return false;
  }}
  
  // Invalid day is taken care of other ways. Don't worry about it here.
  
  return true;
}};  // Ends date_is_not_ready_for_min_max()

function has_valid_day(element) {{
  /** Given a date part element, returns true if:
  *   - the day is <= 31 and year or month is empty
  *   - all fields are filled and the day date is <= max days in the given month in the given year
  *   Returns false if either:
  *   - The day date is > 31 or
  *   - The day date is > the max days in the given month of the given year
  *
  * Inspired by https://github.com/uswds/uswds/blob/728ba785f0c186e231a81865b0d347f38e091f96/packages/usa-date-picker/src/index.js#L735
  * 
  * @param element {{HTML Node}} Any element in the al three parts date picker
  * 
  * @returns bool True if day date is valid
  * 
  * @examples:
  * 10//2000  // true
  * /10/2000  // true
  * 10/10/2000  // true
  * /42/2000  // false
  * 2/29/2021  // false
  */
  var data = get_date_data(element);

  if (parseInt(data.day) > 31) {{
    return false;
  }}
  // Don't invalidate if the date is only partly filled. Empty input fields
  // should get handled other places.
  if (data.year === '' || data.month === '' || data.day === '') {{
    return true;
  }}

  const dateStringParts = [data.year, data.month, data.day];
  const [year, month, day] = dateStringParts.map((str) => {{
    let value;
    const parsed = parseInt(str, 10);
    if (!Number.isNaN(parsed)) value = parsed;
    return value;
  }});
  
  // WARNING: If we change the `type` of the year or day
  // to be 'text', we need to check return false if any
  // dateStringParts part === null. See inspiration link.
  
  const checkDate = setDate({{
    year: year,
    month: month - 1,
    date: day
  }});

  // 12/32/2000 would have transformed into 1/1/2001
  if (
    checkDate.getFullYear() !== year ||
    checkDate.getMonth() !== (month - 1) ||
    checkDate.getDate() !== day
  ) {{
    return false;
  }}

  return true;
}};  // Ends has_valid_day()

function setDate({{year, month, date}}) {{
  /**
  * Set date from month day year
  *
  * @param {{number}} year the year to set
  * @param {{number}} month the month to set (zero-indexed)
  * @param {{number}} date the date to set
  * 
  * @returns {{Date}} the set date
  */
  const newDate = new Date(0);
  newDate.setFullYear(year, month, date);
  return newDate;
}};
  
  
// ==================================================
// ===== Visual feedback management =====
// ==================================================
  
function set_up_errorPlacement(validator) {{
  /** Sometimes override existing errorPlacement.
  *
  * @param {{obj}} validator The form's validator object.
  * 
  * @returns undefined
  */
  let original_error_placement = validator.settings.errorPlacement;
  validator.settings.errorPlacement = function al_errorPlacement(error, field) {{
    /** Put all errors in one spot at the bottom of the parent.
    *   Only runs once per field.
    *   WARNING: If submission validation happens first, this function will
    *   not be run and the error won't be placed inside our AL date.
    */
    let $al_date = get_$al_date(field);
    // If this isn't an AL date, use the original behavior
    if (!$al_date[0] && original_error_placement !== undefined) {{
      original_error_placement(error, field);
      return;
    }}

    $(error).appendTo($al_date.find('.al_error')[0]);
  }};  // Ends al_errorPlacement()
  
}};  // Ends set_up_errorPlacement()
  
function set_up_highlight(validator) {{
  /** For our date elements, override pre-existing highlight method.
  *
  * @param {{obj}} validator The form's validator object.
  * 
  * @returns undefined
  */
  let original_highlight = validator.settings.highlight;
  validator.settings.highlight = function al_highlight(field, errorClass, validClass) {{
    /** Highlight parent instead of individual fields. MVP */
    let $al_date = get_$al_date(field);
    // If this isn't an AL date, use the original behavior
    if (!$al_date[0] && original_highlight !== undefined) {{
      original_highlight(field, errorClass, validClass);
      return;
    }}
    
    $al_date.addClass('al_invalid');
    // Avoid highlighting individual elements
    $al_date.find('.al_field').each(function(index, field) {{
      $(field).removeClass('is-invalid');  // Just a Bootstrap class
      // TODO: try just the below alone
      $(field).removeClass(errorClass);  // Just a Bootstrap class
    }});
    
  }};  // Ends al_highlight()
}};  // Ends set_up_highlight()
  
function set_up_unhighlight(validator) {{
  /** For our date elements, override pre-existing highlight method.
  *
  * @param {{obj}} validator The form's validator object.
  * 
  * @returns undefined
  */
  let original_unhighlight = validator.settings.unhighlight;
  validator.settings.unhighlight = function al_unhighlight(field, errorClass, validClass) {{
    /** Unhighlight parent instead of individual fields. MVP */
    // During invalid required day, this is triggered for month and unhighlights all. Why?
    let $al_date = get_$al_date(field);
    $al_date.removeClass('al_invalid');
    original_unhighlight(field, errorClass, validClass);
  }};  // Ends al_unhighlight()
}};  // Ends set_up_unhighlight()
  
  
}} catch (error) {{
  console.error('Error in AL three parts date CusotmDataTypes', error);
}}

"""


def check_empty_parts(item: str, default_msg="{} is not a valid date") -> Optional[str]:
    # This only handles US dates. How do we use a locale-specific date?
    parts = item.split("/")
    empty_parts = [part == "" for part in parts]
    if len(empty_parts) != 3:
        return word(default_msg).format(item)
    if not any(empty_parts):
        return None
    if all(empty_parts):
        return word("Enter a month, a day, and a year")
    elif sum(empty_parts) == 2:
        # only on part was given, enumerate each
        if not empty_parts[0]:
            return word("Enter a day and a year")
        elif not empty_parts[1]:
            return word("Enter a month and a year")
        else:
            return word("Enter a month and a day")
    elif sum(empty_parts) == 1:
        if empty_parts[0]:
            return word("Enter a month")
        elif empty_parts[1]:
            return word("Enter a day")
        else:
            return word("Enter a year")
    else:
        return word(default_msg).format(item)


class ThreePartsDate(CustomDataType):
    name = "ThreePartsDate"
    input_type = "ThreePartsDate"
    javascript = js_text.format(month=word("Month"), day=word("Day"), year=word("Year"))
    jq_message = word("Answer with a valid date")
    is_object = True
    # Unable to get messages for plain `min`/`max` attributes
    # Unable to use `-` in names for validation plugin.
    # Unable to use `_` in names which da turns into `-`
    mako_parameters = [
        "alMin",
        "alMinMessage",
        "alMax",
        "alMaxMessage",
        "alInvalidDayMessage",
        "alInvalidYearMessage",
        "alDefaultMessage",
    ]

    @classmethod
    def validate(cls, item: str):
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
                    ex_msg = f"{ item } {word('is not a valid date')}"
                    raise DAValidationError(ex_msg)
                return True
            else:
                msg = check_empty_parts(item)
                if msg:
                    raise DAValidationError(msg)

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
    javascript = js_text.format(
        month=word("Month"), day=word("Day"), year=word("Year")
    ).replace("ThreePartsDate", "BirthDate")
    jq_message = word("Answer with a valid date of birth")
    is_object = True
    # Unable to get messages for plain `min`/`max` attributes
    # Unable to use `-` in names for validation plugin.
    # Unable to use `_` in names which da turns into `-`
    mako_parameters = [
        "alMin",
        "alMinMessage",
        "alMax",
        "alMaxMessage",
        "alInvalidDayMessage",
        "alInvalidYearMessage",
        "alDefaultMessage",
    ]

    @classmethod
    def validate(cls, item: str):
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
                raise DAValidationError(word("{} is not a valid date").format(item))
            if matches_date_pattern:
                date_diff = date_difference(starting=date, ending=today())
                if date_diff.days >= 0.0:
                    return True
                else:
                    raise DAValidationError(
                        word(
                            "Answer with a <strong>date of birth</strong> ({} is in the future)"
                        ).format(item)
                    )
            else:
                msg = check_empty_parts(
                    item, default_msg="{} is not a valid <strong>date of birth</strong>"
                )
                if msg:
                    raise DAValidationError(msg)
