from docassemble.webapp.jsonstore import (
    read_answer_json,
    write_answer_json,
    JsonStorage,
    JsonDb,
)
from docassemble.base.generate_key import random_alphanumeric
from docassemble.base.functions import get_current_info
from docassemble.base.util import variables_snapshot_connection, user_info, DADict
import random
from typing import Dict, List, Any, Optional

__all__ = ["save_input_data"]


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

    Args:
        title (str, optional): A descriptive title for this data entry.
            Defaults to "".
        input_dict (Optional[Dict[str, Any]], optional): Dictionary mapping field
            names to their values from interview questions. Values can be strings,
            floats, ints, or DADict objects. If None, an empty dict is used.
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
    ```python
        >>> survey_data = {
        ...     "age": 25,
        ...     "income": 50000.0,
        ...     "interests": my_checkbox_dict
        ... }
        >>> save_input_data("User Survey", survey_data, ["survey", "demographics"])
    ```
    """
    type_dict: Dict[str, str] = {}
    field_dict: Dict[str, Any] = {}
    if not input_dict:
        # Can still save the tags, so just use an empty input dict
        input_dict = {}
    for k, v in input_dict.items():
        field_dict[k] = v
        if isinstance(v, int):
            type_dict[k] = "int"
        elif isinstance(v, float):
            type_dict[k] = "float"
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
                data_to_save[k + "_" + subkey] = subvalue
        else:
            data_to_save[k] = field_dict[k]

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
