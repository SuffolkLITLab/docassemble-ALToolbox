import re
from .copy_button import *
from base64 import b64encode

__all__ = ["display_template"]


def display_template(
    template,
    scrollable=True,
    collapse=False,
    copy=False,
    classname="bg-light",
    class_name=None,  # deprecated
) -> str:
    """
    Display a template with optional scrolling, collapsing, and copy functionality.

    Renders a template in a styled container with various display options including
    scrollable content, collapsible sections, and copy-to-clipboard functionality.
    Supports both the current `classname` parameter and the deprecated `class_name`
    parameter for backwards compatibility.

    Args:
        template: A docassemble template object with content to display.
        scrollable (bool, optional): Whether the content should be scrollable.
            Defaults to True.
        collapse (bool, optional): Whether the content should be collapsible.
            Defaults to False.
        copy (bool, optional): Whether to include a copy-to-clipboard button.
            Defaults to False.
        classname (str, optional): CSS class name for styling the container.
            Defaults to "bg-light".
        class_name (str, optional): Deprecated parameter for CSS class name.
            Defaults to None.

    Returns:
        HTML string containing the rendered template with the specified
        display options.

    Example:
    ```python
        >>> display_template(my_template, scrollable=True, collapse=True)
        '<div id="..." class="al_display_template">...</div>'
    ```
    """
    # 1. Initialize
    if scrollable:
        scroll_class = "scrollable-panel"
        adjust_height = ""
    else:
        scroll_class = "not-scrollable"
        adjust_height = (
            f"onmouseover=\"this.style.height = (this.scrollHeight) + 'px';\""
        )

    # Introducing `classname` to try to align with `collapse_template`
    if not class_name:
        class_name = classname
    class_name = class_name.strip()

    container_classname = "al_display_template"

    container_id = (
        b64encode(str(template.instanceName).encode()).decode().replace("=", "")
    )
    contents_id = f"{ container_id }_contents"
    subject_id = f"{ container_id }_subject"

    # A template with a subject gives us a visible heading we can point
    # screen readers at with aria-labelledby, so the scrollable region has
    # an accessible name instead of just being an unlabeled tab stop.
    if template.subject and template.subject.strip():
        subject_content = template.subject_as_html(trim=True)
        has_subject = bool(subject_content.strip())
    else:
        subject_content = ""
        has_subject = False

    # tabindex="0" is only needed so keyboard/Safari users can scroll the
    # panel; a non-scrollable panel has nothing to scroll into focus.
    focus_attr = ' tabindex="0"' if scrollable else ""
    # aria-labelledby requires a naming-capable role: a plain <div> has the
    # implicit ARIA role "generic", which ARIA 1.2 forbids from being named.
    # Only add role="region" (and the label) when there's both a real
    # subject and something scrollable to name as a region.
    region_attr = (
        f' role="region" aria-labelledby="{subject_id}"'
        if scrollable and has_subject
        else ""
    )

    subject_html = ""
    subject_span = '<span class="subject"></span>'
    if has_subject:
        subject_html = f'<div class="panel-heading"><h3 class="subject" id="{subject_id}">{subject_content}</h3></div>'
        subject_span = (
            f'<span class="subject" id="{subject_id}">{subject_content}</span>'
        )

    # 2. If copiable, call copy_button_html() to generate the template content along with a copy button
    if copy:
        contents = copy_button_html(
            template,
            copy_template_block=True,
            scroll_class=scroll_class,
            style_class=class_name,
            adjust_height=adjust_height,
            aria_labelledby=subject_id if has_subject else "",
        )

        # 2.1 If collapsible, add collapsible elements to the output
        if collapse:
            return f'<div id="{container_id}" class="{container_classname}"><a class="collapsed al_toggle" data-bs-toggle="collapse" href="#{contents_id}" role="button" aria-expanded="false" aria-controls="{contents_id}"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span>{subject_span}</a><div class="collapse" id="{contents_id}">{contents}</div></div>'

        # 2.2 If not collapsible, simply return output from copy_button_html()
        else:
            return f"""
<div id="{container_id}" class="{container_classname}">
{subject_html}
{contents}
</div>
"""

    # 3. If not copiable, generate the whole output
    else:
        if collapse:
            return f'<div id="{container_id}" class="{container_classname}"><a class="collapsed al_toggle" data-bs-toggle="collapse" href="#{contents_id}" role="button" aria-expanded="false" aria-controls="{contents_id}"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span>{subject_span}</a><div class="collapse" id="{contents_id}"><div{focus_attr}{region_attr} class="{scroll_class} card card-body {class_name} pb-1">{template.content_as_html()}</div></div></div>'

        else:
            return f'<div id="{container_id}" class="{container_classname} {scroll_class} card card-body {class_name} pb-1"{focus_attr}{region_attr}>{subject_html}<div>{template.content_as_html()}</div></div>'
