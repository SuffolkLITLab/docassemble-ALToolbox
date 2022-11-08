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
    This function is used by survey type interviews to save input data for data reporting purposes.

    The input_dict should a dictionary where each key is a string and each value is a value from a Docassemble interview
    question. Typically that is a string, float, int, or a DADict.
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
