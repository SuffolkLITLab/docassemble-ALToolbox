from docassemble.base.generate_key import random_alphanumeric
from docassemble.base.functions import get_current_info, safe_json
from docassemble.base.util import DADict, DAObject
from datetime import date, time
from decimal import Decimal
from typing import Dict, List, Any, Optional

try:
    from docassemble.webapp.jsonstorage.helpers import JsonStorage
    from docassemble.webapp.extensions import db

    JsonDb = db.session
except ImportError:
    from docassemble.webapp.jsonstore import JsonStorage  # type: ignore[no-redef]

    try:
        from docassemble.webapp.jsonstore import JsonDb  # type: ignore[no-redef]
    except ImportError:
        from docassemble.webapp.jsonstore import db  # type: ignore[no-redef]

        JsonDb = db.session  # type: ignore[no-redef]


__all__ = ["save_input_data"]


def _serialize_input_value(value: Any) -> Any:
    """Keep data types where possible, preferring useful object display text."""
    if value is None or isinstance(
        value, (str, bool, int, float, date, time, Decimal, list, dict, set, tuple)
    ):
        # Keep containers structured and dates/numbers in safe_json's standard
        # format. safe_json does not recursively serialize tuples, so use a list.
        return safe_json(list(value) if isinstance(value, tuple) else value)

    string_method = type(value).__str__
    if string_method is not object.__str__ and (
        string_method is not DAObject.__str__ or hasattr(value, "name")
    ):
        # DAObject's default string is just its variable name unless it has a
        # name attribute. Other overrides (including inherited ones) can give
        # useful display text, such as an individual's full name.
        try:
            return str(value)
        except Exception:
            # For example, a DAList may not yet be gathered or a display method
            # may depend on an undefined interview variable.
            pass
    return safe_json(value)


def save_input_data(
    title: str = "",
    input_dict: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> None:
    """
    Save survey interview input data to JSON storage for data reporting purposes.

    Processes and stores user input data from survey-type interviews into the
    Docassemble JSON storage system. Automatically handles type inference and
    flattening of complex data structures like checkboxes and multiselect fields.
    Dates use ISO format and Decimals become floats. Objects with a useful
    ``__str__`` method are saved as display text (for example, an individual's
    name); other objects and native containers are serialized with ``safe_json``.
    If an object's string method raises an exception, ``safe_json`` is used instead.

    Args:
        title (str, optional): A descriptive title for this data entry.
            Defaults to "".
        input_dict (Optional[Dict[str, Any]], optional): Dictionary mapping field
            names to their values from interview questions, including primitives,
            dates, Decimals, containers, and Docassemble objects. If None, an
            empty dict is used.
            Defaults to None.
        tags (Optional[List[str]], optional): List of string tags to associate
            with this data entry for categorization and filtering. Defaults to None.

    Note:
        - This function saves data to storage but does not return anything
        - Checkbox and multiselect fields (DADict) are automatically flattened
          so each option becomes a separate database column with a boolean value
        - Each call creates one database record per interview session
        - Data is stored with a random 32-character alphanumeric key

    Example:
    After collecting `feedback_was_helpful` and `feedback_comments`, call
    this once in the feedback submission flow:

    **Input (interview YAML)**

    ```yaml
    code: |
      save_input_data(
          title="Interview feedback",
          input_dict={"helpful": feedback_was_helpful, "comments": feedback_comments},
          tags=["feedback"],
      )
      feedback_saved = True
    ```
    """
    type_dict: Dict[str, str] = {}
    field_dict: Dict[str, Any] = {}
    if not input_dict:
        # Can still save the tags, so just use an empty input dict
        input_dict = {}
    for k, v in input_dict.items():
        field_dict[k] = v
        if isinstance(v, bool):
            type_dict[k] = "bool"
        elif isinstance(v, int):
            type_dict[k] = "int"
        elif isinstance(v, (float, Decimal)):
            type_dict[k] = "float"
        elif isinstance(v, date):
            type_dict[k] = "date"
        elif isinstance(v, DADict):  # This covers checkboxes and multiselect
            type_dict[k] = "checkboxes"
        else:
            type_dict[k] = "text"

    data_to_save: Dict[str, Any] = {}
    data_to_save["title"] = title

    # TODO(qs): We should be able to infer type in the InterviewStats package too, eventually. But
    # leaving as-is for now
    data_to_save["field_type_list"] = type_dict  # This may not be needed

    for k, v in type_dict.items():
        # If a field is of checkboxes type, flatten its elements dict
        # so that each key/value pair is saved in its own column.
        if v in ["checkboxes", "multiselect"]:
            for subkey, subvalue in field_dict[k].elements.items():
                data_to_save[f"{k}_{subkey}"] = _serialize_input_value(subvalue)
        else:
            data_to_save[k] = _serialize_input_value(field_dict[k])

    # Save one record per session to JsonStorage datatable.
    filename = get_current_info().get("yaml_filename", None)
    random_uid = random_alphanumeric(32)
    new_entry = JsonStorage(
        filename=filename,
        key=random_uid,
        data=data_to_save,
        tags=tags,
        persistent=False,
    )
    JsonDb.add(new_entry)
    JsonDb.commit()
