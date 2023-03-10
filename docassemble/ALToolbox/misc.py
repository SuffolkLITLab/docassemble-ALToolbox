from typing import Optional, Union

from decimal import Decimal
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
    "review_widget",
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
def thousands(num: Union[float, str, Decimal], show_decimals=False) -> str:
    """
    Return a whole number formatted with thousands separator.
    Optionally, format with 2 decimal points (for a PDF form with the
    currency symbol already present in the form)

    If `show_decimals`, will call `int(num)`, truncating the decimals instead of
    rounding to the closest int.
    """
    try:
        if show_decimals:
            return f"{num:,.2f}"
        else:
            return f"{int(num):,}"
    except:
        return str(num)


def tel(phone_number) -> str:
    """Format a phone number so you can click on it to open in your phone dialer"""
    return '<a href="tel:' + str(phone_number) + '">' + str(phone_number) + "</a>"


def fa_icon(
    icon: str,
    color: Optional[str] = "primary",
    color_css: Optional[str] = None,
    size: Optional[str] = "sm",
    fa_class: str = "fa-solid",
) -> str:
    """Display a fontawesome icon inline.

    Docassemble allows you to display an icon from [fontawesome](https://fontawesome.com),
    but it does not provide control over the size or color of the icon. This function gives
    you more control over the icon that is inserted.

    Args:
      icon: a string representing a fontawesome icon. The icon needs to be in the
        [free library](https://fontawesome.com/search?o=r&m=free).
      color: can be any [Bootstrap color variable](https://getbootstrapc.mo/docs/4.0/utilities/colors).
        For example: `primary`, `secondary`, `warning`
      color_css: allows you to use a CSS code to represent the color, e.g., `blue`, or `#fff` for black
      size: used to control the [fontawesome size](https://fontawesome.com/v6.0/docs/web/style/size)
        (without the `fa-` prefix). Valid values include `2xs`, `xs`, the default of `sm`,
        `md`, `lg`, `xl`, `2x1`, and the python `None`, which defaults to `md`.
      fa_class: let's you specify the fontawesome class, needed for any icon that isn't
        the default class of `fa-solid`, like `fa-brands`, or `fa-regular` and `fa-light`.

    Returns:
      HTML for a font-awesome icon of the specified size and color.
    """
    if not size or size == "md":
        size_str = ""
    else:
        size_str = " fa-" + size
    if not size and not color and not color_css:
        return ":" + icon + ":"  # Default to letting Docassemble handle it
    if color_css:
        return (
            f'<i class="{fa_class} fa-'
            + icon
            + size_str
            + '" style="color:'
            + color_css
            + ';"></i>'
        )
    if color:
        return (
            f'<i class="{fa_class} fa-'
            + icon
            + size_str
            + '" style="color:var(--'
            + color
            + ');"></i>'
        )
    return f'<i class="{fa_class} fa-{icon}{size_str}"></i>'


def space(var_name: str, prefix=" ", suffix="") -> str:
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


def yes_no_unknown(
    var_name: str, condition: Optional[bool], unknown="Unknown", placeholder=0
):
    """Return 'unknown' if the value is None rather than False. Helper for PDF filling with
    yesnomaybe fields"""
    if condition:
        return value(var_name)
    elif condition is None:
        return unknown
    else:
        return placeholder


def number_to_letter(n: Optional[int]) -> str:
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


def collapse_template(
    template,
    classname=None,
    closed_icon="caret-right",
    open_icon="caret-down",
):
    """
    Insert HTML for a Bootstrap "collapse" div.

    Optionally, you can specify a custom icon to override the defaults:

    The default icons are "right caret" which displays when the text is collapsed (`closed_icon`) and
    "down caret" which displays when the text is open (`open_icon`).
    """
    if not template.subject_as_html(trim=True) and not template.content_as_html():
        return ""
    if classname is None:
        classname = " bg-light"
    else:
        classname = " " + classname.strip()
    the_id = re.sub(r"[^A-Za-z0-9]", "", template.instanceName)
    return f"""\
<a class="collapsed" data-bs-toggle="collapse" href="#{ the_id }" role="button" aria-expanded="false" aria-controls="{ the_id }"><span class="pdcaretopen">{ fa_icon(open_icon) }</span><span class="pdcaretclosed">{ fa_icon(closed_icon) }</span> { template.subject_as_html(trim=True) }</a>
<div class="collapse" id="{ the_id }"><div class="card card-body pb-1{ classname }">{ template.content_as_html() }</div></div>\
"""


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


def review_widget(
    *,
    up_action: str,
    down_action: str,
    review_action: Optional[str] = None,
    thumbs_display: str = "Did we help you?",
    review_display: str = "Thank you for your feedback. Let us know what we could do better",
    submit_review_button: str = "Add your review",
    post_review_display: str = "Thank you for your review!",
) -> str:
    """
    A widget that allows people to give a quick review (thumbs up and down, with an optional text
    component) in the middle of an interview without triggering a page reload.

    If `review_action` is provided, once you press either of the thumbs, a text input screen with
    a submit button appears, and once the text review is submitted (or after the thumbs, if no
    `review_action` was provided), a final "thank you" message is displayed.

    Args:
        up_action: the variable name of an event to be executed on the server if the
            thumbs up is pressed
        down_action: the variable name of an event to be executed on the server if the
            thumbs down is pressed
        review_action: the variable name of an event to be execute on the
            server when someone submits their text review
        thumbs_display: text displayed to user describing the thumbs
        review_display: text displayed to user describing the text input
        submit_review_button: text on the button to submit their text review
        post_review_display: text displayed to user after review is submitted
    Returns:
        the HTML string of the widget
    """
    js_thumbs_up = f"javascript:altoolbox_thumbs_up_send('{up_action}', {'true' if review_action else 'false'})"
    js_thumbs_down = f"javascript:altoolbox_thumbs_down_send('{down_action}', {'true' if review_action else 'false'})"
    widget = f"""
<div class="card" style="width: 20rem;">
  <div class="card-body">
    <p class="al-thumbs-widget">{word(thumbs_display)}</p>
    <a href="{js_thumbs_up}" id="al-thumbs-widget-up"
        class="btn btn-md btn-info al-thumbs-widget" aria-label="{word('Thumbs up')}">{fa_icon('thumbs-up', size='md')}</a>
    <a href="{js_thumbs_down}" id="al-thumbs-widget-down"
        class="btn btn-md btn-info al-thumbs-widget" aria-label="{word('Thumbs down')}">{fa_icon('thumbs-down', size='md')}</a>
    """
    if review_action:
        review_area_id = review_action + "_area_id"
        js_review = (
            f"javascript:altoolbox_review_send('{review_action}', '{review_area_id}')"
        )
        widget += f"""
      <p class="al-review-text al-hidden">{word(review_display)}</p>
      <textarea class="datextarea al-review-text al-hidden" id="{review_area_id}"
          alt="{word('Write your review here')}" rows="4"></textarea>
      <br class="al-review-text">
      {action_button_html(js_review, label=word(submit_review_button), size='md', classname='al-review-text al-hidden')} 
        """
    widget += f"""
  <p class="al-after-review al-hidden">{word(post_review_display)}</p>
  </div>
</div>"""
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
    """Generate a conditional checkbox for docx templates

    Args:
      checked_value: defaults to `[X]` but can be set to any string or even a `DAFile` or `DAStaticFile`
          with the image of a checkbox
      unchecked_value: opposite meaning of `checked_value` and defaults to `[  ]`

    """
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
