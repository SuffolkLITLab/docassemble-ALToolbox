import re
from .copy_button import *


def display_template(
    template, scrollable=True, collapse=False, copy=False, class_name="bg-light"
):
    # 1. Initialize
    if scrollable:
        scroll_class = "scrollable-panel"
        adjust_height = ""
    else:
        scroll_class = "not-scrollable"
        adjust_height = (
            f"onmouseover=\"this.style.height = (this.scrollHeight) + 'px';\""
        )

    class_name = class_name.strip()

    the_id = re.sub(r"[^A-Za-z0-9]", "", template.instanceName)

    # 2. If copiable, call copy_button_html() to generate the template content along with a copy button
    if copy:
        text = copy_button_html(
            template,
            copy_template_block=True,
            scroll_class=scroll_class,
            style_class=class_name,
            adjust_height=adjust_height,
        )

        # 2.1 If collapsible, add collapsible elements to the output
        if collapse:
            return f'<a class="collapsed" data-bs-toggle="collapse" href="#{the_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="pdcaretclosed"><i class="fas fa-caret-right"></i></span> {template.subject_as_html(trim=True)}</a><div class="collapse" id="{the_id}">{text}</div>'

        # 2.2 If not collapsible, simply return output from copy_button_html()
        else:
            return text

    # 3. If not copiable, generate the whole output
    else:
        if not collapse:
            return f'<div class="{scroll_class} card card-body {class_name} pb-1" id="{the_id}"><div class="panel-heading"><h3>{template.subject_as_html(trim=True)}</h3></div>{template.content_as_html()}</div>'

        else:
            return f'<a class="collapsed" data-bs-toggle="collapse" href="#{the_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="pdcaretclosed"><i class="fas fa-caret-right"></i></span>{template.subject_as_html(trim=True)}</a><div class="collapse" id="{the_id}"><div class="{scroll_class} card card-body {class_name} pb-1">{template.content_as_html()}</div></div>'
