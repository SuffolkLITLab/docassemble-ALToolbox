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

js_text = """\
// This is an adaptation of Jonathan Pyle's datereplace.js

/*
* Notes to keep around:
* - Rule names must avoid dashes.
* - Hidden custom datatype elements are not disabled on first load. Disable them ourselves.
* - Our custom highlighting doesn't work on submit. It might be because it's the original date validation going on.
* - Avoid a min date default for birthdays. Too hard to predict developer
*   needs, like great-grandmother's birthday. Document that developers need
*   to set a min value if they want one.
* - Year input of "1" counts as a date of 2001 and "11" is 2011
* - Only handles US formatted dates
* 
* TODO: (post MVP)
*   - Get the 'Month'/'Day'/'Year' word values as mako_parameters too so
*     they can be translated. Pretty easy.
*   - On submit, validation feedback shows up for the original date field
*     separately from the other fields. Possibly add the original date field
*     to the list of elements that have shared validation feedback (like month, day, year).
*   - Deal with internation user date input and international dev date attributes
*
* Post MVP validation priority (https://design-system.service.gov.uk/components/date-input/#error-messages):
*  1. missing or incomplete information (when parent is no longer in focus, highlight fields missing info?)
*  2. information that cannot be correct (for example, the number ‘13’ in the month field)
*     (Maybe less than 4 digits in year counts? Maybe it's #3 priority?)
*  3. information that fails validation for another reason
* Or validate from left to right
*
* For invalidation styling see al_split_dates.css.
*/

// da doesn't log the full error sometimes, so we'll do our own try/catch
try {{

$(document).on('daPageLoad', function(){{
  $('input[type="ThreePartsDate"]').each(function(){{
    let $al_date = replace_date(this);
    //set_up_validation($al_date);
  }});  // ends for each date datatype
}});  // ends on da page load
  
  
function replace_date(original_date) {{
  /** Replace the original date element with our 3 fields and
  *   make sure the fields update the original date value.
  * 
  * @param {{HTML Node}} date The original date element.
  * 
  * @returns {{jQuery obj}} AL container for all the split date elements
  */
  let $original_date = $(original_date);
  $original_date.hide();
  $original_date.attr('type', 'hidden');
  $original_date.attr('aria-hidden', 'true');
  
  var $al_date = $('<div class="al_split_date form-row row">');
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
  // Updates will be triggered when the user leaves an input field
  $year.on('change', update);
  $month.on('change', update);
  $day.on('change', update);
  function update() {{
    update_original_date($al_date);
  }};
  
  return $al_date;
}};  // Ends replace_date()
  

// A shame these have to be split into month and others
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
  var id = date_id + '_' + type;
  // '_ignore' prevents the field from being submitted, avoiding a da error
  let name =  '_ignore_' + id;
  
  // For python formatting, need to have {{day}} and {{year}}
  let $label = '';
  if (type === 'day') {{
    $label = $('<label for="' + name + '">{{day}}</label>');
  }} else {{
    $label = $('<label for="' + name + '">{{year}}</label>');
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
  // There's only one message element, so all fields are described by it
  // I think jquery validation plugin uses the error message's `for` attrib,
  // but I'm not sure where that originally comes from. Looks like the original
  // input's `id`, but I'm not sure why the plugin is using that.
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
  
  let id = date_id + '_month';
  // '_ignore' prevents the field from being submitted, avoiding a da error
  let name =  '_ignore_' + id;
  
  let $label = $('<label for="' + name + '">{{month}}</label>');
  $col.append($label);
  
  // aria-describedby is ok to have, even when the date-part error is
  // not present or is display: none
  // `for` is label of field while `aria-describedby` is supplemental info
  // https://developer.mozilla.org/en-US/docs/Web/CSS/display#display_none
  // https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-hidden
  
  // There's only one message element, so all fields are described by it
  // I think jquery validation plugin uses the error message's `for` attrib,
  // but I'm not sure where that originally comes from. Looks like the original
  // input's `id`, but I'm not sure where the plugin is getting that.
  var $field = $('<select class="form-select al_field month ' + date_id + '">');  // unique
  $field.attr('id', id);
  $field.attr('name', name);
  // There's only one message element, so all fields are described by it
  $field.attr('aria-describedby', date_id + '-error');
  add_month_options($field);  // unique
  
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
  
  // "No month selected" option
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
  * @param {{$ obj}} $al_date jQuery obj of the al parent of our split date parts.
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
  
  // TODO: Select "" if month is empty string?
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
  * @param {{$ obj}} $al_date The al parent of our split date parts.
  * 
  * @returns undefined
  */
  let $original_date = get_$original_date($al_date);
  let $error = $('<div id="al_' + $original_date.attr('id') + '_error" class="da-has-error al_error"></div>');
  $al_date.append($error);
  return $error;
}};  // Ends add_error_container()
  

function update_original_date($al_date) {{
  /** Update value in original date field using the values
  *   of the al split date parts.
  * 
  * @param {{$ obj}} $original_date The original date element.
  * @param {{$ obj}} $al_date The al parent of our split date parts.
  * 
  * @returns undefined
  */
  var data = get_date_data($al_date);
  
  let US_date = data.month + '/' + data.day + '/' + data.year;
  if (US_date === '//') {{
    US_date = '';
  }}
  
  let val_date = US_date;
  
  // // TODO: If all fields are filled in, we can use the user's locale
  // // settings to create the date Should we avoid this? US person only
  // // visiting the UK, not living there? Regardless, right now its not
  // // possible to work out the complexity of storing and validating
  // // dates of multiple formats. Note that `Date` will fill in the
  // // blanks for any empty string.
  // if (data.month !== '' && data.day !== '' && data.year !== '') {{
  //   // ISO date
  //   val_date = new Date(iso_date).toLocaleDateString(undefined, {{ day: '2-digit', month: '2-digit', year: 'numeric' }})
  // }}
  
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
  * @param {{Node}} element AL split date element. Can be parent of date parts.
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
  * @param {{HTML Node | $ obj}} element Any al split date element, including parent.
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
  * @param {{HTML Node}} element Any al split date element, including al parent.
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
  * @param {{HTML Node}} element Any al split date element, including al parent.
  * 
  * @returns {{jQuery obj}}
  */
  return $($(element).closest('.dafieldpart').children('input')[0]);
}};  // Ends get_$original_date()
  
  
function get_$al_date(element) {{
  /** Return the element we created to surround our date elements.
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
  return $(element).closest('.al_split_date');
}};  // Ends get_$al_date()
  
  
  
}} catch (error) {{
  console.error('Error in AL date CusotmDataTypes', error);
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
    ## Probably won't work because the input to validate is hidden
    #jq_rule = "date"

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
    ## Probably won't work because the input to validate is hidden
    #jq_rule = "date"

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
