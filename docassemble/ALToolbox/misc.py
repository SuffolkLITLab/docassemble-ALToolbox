import docassemble.base.functions
from docassemble.base.util import (
    defined,
    value,
    showifdef,
    space_to_underscore,
    action_button_html,
    Address,
    word,
)
import re

__all__ = [
    "shortenMe",
    "thousands",
    "tel",
    "fa_icon",
    "space",
    "yes_no_unknown",
    "number_to_letter",
    "collapse_template",
    "tabbed_templates_html",
    "reaction_widget",
    "sum_if_defined",
    "add_records",
    "output_checkbox",
    "nice_county_name",
]


class shortenMe:
    def __init__(self, originalURL):
        self.shortenedURL = docassemble.base.functions.temp_redirect(
            originalURL, 60 * 60 * 24 * 7, False, False
        )


# The following three functions are from Quinten
# format a float number to a whole number with thousands separator
def thousands(num: float, show_decimals=False) -> str:
    """
    Return a whole number formatted with thousands separator.
    Optionally, format with 2 decimal points (for a PDF form with the
    currency symbol already present in the form)
    """
    try:
        if show_decimals:
            return f"{num:,.2f}"
        else:
            return f"{int(num):,}"
    except:
        return num


# Format a phone number so you can click on it to open in your phone dialer
def tel(phone_number):
    return '<a href="tel:' + str(phone_number) + '">' + str(phone_number) + "</a>"


# Display an icon on the screen.
def fa_icon(icon, color="primary", color_css=None, size="sm"):
    """
    Return HTML for a font-awesome icon of the specified size and color. You can reference
    a CSS variable (such as Bootstrap theme color) or a true CSS color reference, such as 'blue' or
    '#DDDDDD'. Defaults to Bootstrap theme color "primary".

    Sizes can be '2xs', 'xs', 'sm', 'md' (or None), 'lg', 'xl', '2xl'.
    """
    if not size or size == "md":
        size_str = ""
    else:
        size_str = " fa-" + size
    if not size and not color and not color_css:
        return ":" + icon + ":"  # Default to letting Docassemble handle it
    elif color_css:
        return (
            '<i class="fa fa-'
            + icon
            + size_str
            + '" style="color:'
            + color_css
            + ';"></i>'
        )
    else:
        return (
            '<i class="fa fa-'
            + icon
            + size_str
            + '" style="color:var(--'
            + color
            + ');"></i>'
        )


def space(var_name, prefix=" ", suffix=""):
    """If the value as a string is defined, return it prefixed/suffixed. Defaults to prefix
    of a space. Helps build a sentence with less cruft. Equivalent to SPACE function in
    HotDocs."""
    if (
        var_name
        and isinstance(var_name, str)
        and re.search(r"[A-Za-z][A-Za-z0-9\_]*", var_name)
        and defined(var_name)
        and value(var_name)
    ):
        return prefix + showifdef(var_name) + suffix
    else:
        return ""


def yes_no_unknown(var_name, condition, unknown="Unknown", placeholder=0):
    """Return 'unknown' if the value is None rather than False. Helper for PDF filling with
    yesnomaybe fields"""
    if condition:
        return value(var_name)
    elif condition is None:
        return unknown
    else:
        return placeholder


def number_to_letter(n):
    """Returns a capital letter representing ordinal position. E.g., 1=A, 2=B, etc. Appends letters
    once you reach 26 in a way compatible with Excel/Google Sheets column naming conventions. 27=AA, 28=AB...
    """
    string = ""
    if n is None:
        n = 0
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def collapse_template(template, classname=None):
    """
    Insert HTML for a Bootstrap "collapse" div.
    """
    if not template.subject_as_html(trim=True) and not template.content_as_html():
        return ""
    if classname is None:
        classname = " bg-light"
    else:
        classname = " " + classname.strip()
    the_id = re.sub(r"[^A-Za-z0-9]", "", template.instanceName)
    return """\
<a class="collapsed" data-bs-toggle="collapse" href="#{}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="pdcaretclosed"><i class="fas fa-caret-right"></i></span> {}</a>
<div class="collapse" id="{}"><div class="card card-body{} pb-1">{}</div></div>\
""".format(
        the_id,
        template.subject_as_html(trim=True),
        the_id,
        classname,
        template.content_as_html(),
    )


def tabbed_templates_html(tab_group_name: str, *pargs) -> str:
    """
    Provided a list of templates, create Bootstrap v 4.5 tabs with the `subject` as the tab label.
    """
    if isinstance(tab_group_name, str):
        tab_group_name = space_to_underscore(tab_group_name)
    else:
        tab_group_name = "tabbed-group"
    tabs = f'<ul class="nav nav-tabs" id="{tab_group_name}" role="tablist">\n'
    tab_content = '<div class="tab-content" id="myTabContent">'
    for index, templ in enumerate(pargs):
        tab_id = f"{tab_group_name}-{space_to_underscore(str(templ.subject))}"
        tabs += '<li class="nav-item" role="presentation">\n'
        if index == 0:
            tabs += f'<a class="nav-link active" id="{tab_id}-tab" data-bs-toggle="tab" href="#{tab_id}" role="tab" aria-controls="{tab_id}" aria-selected="true">{templ.subject}</a>\n'
            tab_content += f'<div class="tab-pane fade show active" id="{tab_id}" role="tabpanel" aria-labelledby="{tab_id}-tab">\n'
            tab_content += templ.content_as_html()

            tab_content += "\n</div>\n"
        else:
            tabs += f'<a class="nav-link" id="{tab_id}-tab" data-bs-toggle="tab" href="#{tab_id}" role="tab" aria-controls="{tab_id}" aria-selected="false">{templ.subject}</a>\n'
            tab_content += f'<div class="tab-pane fade" id="{tab_id}" role="tabpanel" aria-labelledby="{tab_id}-tab">\n'
            tab_content += templ.content_as_html()
            tab_content += "\n</div>\n"
        tabs += "</li>"
    tabs += "</ul>"
    tab_content += "</div>"

    return tabs + tab_content


def reaction_widget(
    *,
    up_action,
    down_action,
    feedback_action=None,
    thumbs_text="How did you feel about this form?",
    feedback_text="Thanks! You can leave an anonymous review below",
    submit_feedback_text="Submit your feedback",
    post_feedback_text="Thank you for your review!",
) -> str:
    js_thumbs_up = f"javascript:altoolbox_thumbs_up_send('{up_action}', {'true' if feedback_action else 'false'})"
    js_thumbs_down = f"javascript:altoolbox_thumbs_down_send('{down_action}', {'true' if feedback_action else 'false'})"
    widget = f"""
    <div class="card" style="width: 20rem;">
      <div class="card-body">
        <p class="al-thumbs-widget">{word(thumbs_text)}</p>
        <a href="{js_thumbs_up}" id="al-thumbs-widget-up"
            class="btn btn-md btn-info al-thumbs-widget" aria-label="{word('Thumbs up')}">{fa_icon('thumbs-up', size='md')}</a>
        <a href="{js_thumbs_down}" id="al-thumbs-widget-down"
            class="btn btn-md btn-info al-thumbs-widget" aria-label="{word('Thumbs down')}">{fa_icon('thumbs-down', size='md')}</a>
    """
    if feedback_action:
        feedback_id = feedback_action + "_area_id"
        js_feedback = (
            f"javascript:altoolbox_feedback_send('{feedback_action}', '{feedback_id}')"
        )
        widget += f"""
          <p class="al-feedback-text al-hidden">{word(feedback_text)}</p>
          <textarea class="datextarea al-feedback-text al-hidden" id="{feedback_id}"
              alt="{word('Write your feedback here')}" rows="4"></textarea>
          <br class="al-feedback-text">
          {action_button_html(js_feedback, label=word(submit_feedback_text), size='md', classname='al-feedback-text al-hidden')} 
        """
    widget += f"""
      <p class="al-post-feedback al-hidden">{word(post_feedback_text)}</p>
      </div>
    </div>
    """
    return widget


def sum_if_defined(*pargs):
    """Lets you add up the value of variables that are not in a list"""
    total = 0
    for source in pargs:
        if defined(source):
            total += value(source)
    return total


def add_records(obj, labels):
    """List demo interviews in the current package to be run from the landing page"""
    index = 0
    for key, val in labels.items():
        obj.appendObject()
        obj[index].name = key
        obj[index].description = val[0]
        obj[index].reference = val[1]
        index += 1
    return obj


def output_checkbox(
    value_to_check: bool, checked_value: str = "[X]", unchecked_value: str = "[  ]"
):
    """Generate a conditional checkbox for docx templates"""
    if value_to_check:
        return checked_value
    else:
        return unchecked_value


def nice_county_name(address: Address) -> str:
    """
    If the county name contains the word "County", which Google Address
    Autocomplete does by default, remove it.
    """
    if not hasattr(address, "county"):
        return ""
    if address.county.endswith(" County"):
        return address.county[: -len(" County")]
    else:
        return address.county
