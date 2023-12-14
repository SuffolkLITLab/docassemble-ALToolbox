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

    subject_html = ""
    if not template.subject == "":
        subject_html = f'<div class="panel-heading"><h3 class="subject">{template.subject_as_html(trim=True)}</h3></div>'

    # 2. If copiable, call copy_button_html() to generate the template content along with a copy button
    if copy:
        contents = copy_button_html(
            template,
            copy_template_block=True,
            scroll_class=scroll_class,
            style_class=class_name,
            adjust_height=adjust_height,
        )

        # 2.1 If collapsible, add collapsible elements to the output
        if collapse:
            return f'<div id="{container_id}" class="{container_classname}"><a class="collapsed al_toggle" data-bs-toggle="collapse" href="#{contents_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span><span class="subject">{template.subject_as_html(trim=True)}</span></a><div class="collapse" id="{contents_id}">{contents}</div></div>'

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
            return f'<div id="{container_id}" class="{container_classname}"><a class="collapsed al_toggle" data-bs-toggle="collapse" href="#{contents_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span><span class="subject">{template.subject_as_html(trim=True)}</span></a><div class="collapse" id="{contents_id}"><div class="{scroll_class} card card-body {class_name} pb-1">{template.content_as_html()}</div></div></div>'

        else:
            return f'<div id="{container_id}" class="{container_classname} {scroll_class} card card-body {class_name} pb-1" id="{contents_id}">{subject_html}<div>{template.content_as_html()}</div></div>'
