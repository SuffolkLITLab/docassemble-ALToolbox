from docassemble.base.functions import word

__all__ = ["copy_button_html"]


# See GitHub issue https://github.com/SuffolkLITLab/docassemble-ALToolbox/issues/16
def copy_button_html(
    text_to_copy: str,
    text_before: str = "",
    label: str = "Copy",
    tooltip_inert_text: str = "Copy to clipboard",
    tooltip_copied_text: str = "Copied!",
    copy_template_block: bool = False,
    scroll_class: str = "",
    style_class: str = "",
    adjust_height: str = "",
) -> str:
    """
    Return the HTML for a button that will let a user copy the given text.

    Creates a copy-to-clipboard button with customizable styling and tooltip text.
    The button can be configured to display as a simple input field or as a styled
    template block suitable for displaying longer content.

    To use, include `docassemble.ALToolbox:copy_button.yml` in your DA interview.

    Args:
        text_to_copy (str): Text you want the user to be able to copy to clipboard.
        text_before (str, optional): The prompt that will appear to the left of the
            HTML input. Defaults to "".
        label (str, optional): The label text displayed on the copy button.
            Defaults to "Copy".
        tooltip_inert_text (str, optional): Tooltip text shown when hovering over
            the button before it's clicked. Defaults to "Copy to clipboard".
        tooltip_copied_text (str, optional): Tooltip text shown when hovering over
            the button after the text is placed on the clipboard. Defaults to "Copied!".
        copy_template_block (bool, optional): If True, displays the content in a
            textarea with template block styling. If False, uses a simple input field.
            Defaults to False.
        scroll_class (str, optional): CSS class for scroll behavior when using
            template block mode. Defaults to "".
        style_class (str, optional): Additional CSS classes for styling the container.
            Defaults to "".
        adjust_height (str, optional): HTML attributes for height adjustment behavior.
            Defaults to "".

    Returns:
        str: Complete HTML string containing the copy button and associated elements.

    Example:
        >>> copy_button_html("Hello World", text_before="Message:", label="Copy Message")
        '<div class="al_copy">...<button class="btn btn-secondary al_copy_button">...</div>'
    """

    button_str = '<div class="al_copy">\n'
    if text_before != "":
        button_str += (
            f'<span class="al_copy_description">{word( text_before )}</span>\n'
        )

    # Add textarea tag if copy_template_block is True, along with docassemble template block class names
    if copy_template_block:
        button_str += f'<textarea readonly class="card card-body {style_class} bg-light pb-1 al_copy_value {scroll_class}" {adjust_height}>{ text_to_copy }</textarea>\n'

    # Add input tag if copy_template_block is False
    else:
        button_str += f'<input readonly class="al_copy_value" type="text" value="{ text_to_copy }">\n'

    # Add the copy button
    if copy_template_block:
        button_str += f'<button class="btn btn-secondary al_copy_button al_copy_block" type="button">\n'
    else:
        button_str += (
            f'<button class="btn btn-secondary al_copy_button" type="button">\n'
        )

    # Add tooltip texts
    button_str += f'<span class="al_tooltip al_tooltip_inert">{word( tooltip_inert_text )}</span>\n'
    button_str += f'<span class="al_tooltip al_tooltip_active">{word( tooltip_copied_text )}</span>\n'

    # Add icon and label for the button
    button_str += f'<i class="far fa-copy"></i>\n'
    button_str += f"<span>{word( label )}</span></button>\n"
    button_str += f"</div>\n"

    return button_str
