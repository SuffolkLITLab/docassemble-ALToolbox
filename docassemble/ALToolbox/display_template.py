import re
from .copy_button import *


def display_template(
    template,
    scrollable=True,
    collapse=False,
    copy=False,
    classname="bg-light",
    container_classname=None,
    class_name=None,
    container_id_tag=None
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
    
    container_classname_plus = "al_display_template"
    if container_classname:
      container_classname_plus += f" { container_classname }"

    the_id = re.sub(r"[^A-Za-z0-9]", "", template.instanceName)
    actual_container_id_tag = container_id_tag or f"{ the_id }_container"
    
    subject_html = ''
    if not template.subject == "":
      subject_html = f'<div class="panel-heading"><h3 class="subject">{template.subject_as_html(trim=True)}</h3></div>'

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
            return f'<div id="{actual_container_id_tag}" class="{container_classname_plus}"><a class="collapsed" data-bs-toggle="collapse" href="#{the_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span><span class="subject">{template.subject_as_html(trim=True)}</span></a><div class="collapse" id="{the_id}">{text}</div></div>'

        # 2.2 If not collapsible, simply return output from copy_button_html()
        else:
            return f"""
<div id="{actual_container_id_tag}" class="{container_classname_plus}">
{subject_html}
{text}
</div>
"""

    # 3. If not copiable, generate the whole output
    else:
        if not collapse:
            return f'<div id="{actual_container_id_tag}" class="{container_classname_plus} {scroll_class} card card-body {class_name} pb-1" id="{the_id}">{subject_html}<div>{template.content_as_html()}</div></div>'

        else:
            return f'<div id="{actual_container_id_tag}" class="{container_classname_plus}"><a class="collapsed" data-bs-toggle="collapse" href="#{the_id}" role="button" aria-expanded="false" aria-controls="collapseExample"><span class="toggle-icon pdcaretopen"><i class="fas fa-caret-down"></i></span><span class="toggle-icon pdcaretclosed"><i class="fas fa-caret-right"></i></span><span class="subject">{template.subject_as_html(trim=True)}</span></a><div class="collapse" id="{the_id}"><div class="{scroll_class} card card-body {class_name} pb-1">{template.content_as_html()}</div></div></div>'
