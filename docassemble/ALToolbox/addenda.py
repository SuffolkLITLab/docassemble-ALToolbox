__all__ = ["myTable", "myTextList", "safe_json2"]


# This function creates a Table list to be used in an addendum file. Currently it handles 'Thing' and 'Inidvidual' object type of DAList (special name attribute).
class myTable:
    """
    Utility class for creating table representations from DAList objects for addenda.
    
    This class processes DAList objects containing 'Individual' or 'Thing' objects 
    and converts them into structured table format suitable for document addenda.
    It handles data sanitization and formatting for display purposes.
    """
    def __init__(self, tblData, tblTitle, tblHeader):
        """
        Initialize a table from DAList data with title and headers.
        
        Args:
            tblData: A DAList object containing Individual or Thing objects.
            tblTitle (str): The title for the table.
            tblHeader: The column headers for the table.
        """
        # 1. Put the DAList items into a regular list
        recordList = list()
        for w in tblData:
            my_dict = safe_json2(w)
            for key in list(my_dict):
                # determine the class type
                if key == "_class":
                    if my_dict[key] == "docassemble.base.util.Individual":
                        indicator = "Individual"
                    elif my_dict[key] == "docassemble.base.util.Thing":
                        indicator = "thing"
                    else:
                        indicator = "nothing"  # need refinement
                    my_dict.pop(key)  # remove the class item
                elif (
                    key == "instanceName"
                    or key == "address"
                    or key == "location"
                    or key.startswith("_")
                    or key == "complete"
                ):
                    # remove the item from the dictionary
                    my_dict.pop(key)

                # use the indicator to get rid of extra stuff in the name item
                if key == "name":
                    if indicator == "Individual":
                        my_dict[key] = (
                            my_dict[key]["first"] + " " + my_dict[key]["last"]
                        )
                    elif indicator == "thing":
                        my_dict[key] = my_dict["name"]["text"]
            # Save it to a list
            recordList.append(my_dict)

        # 2. Store the table data in a list for the addendum.
        self.tableList = list()
        self.tableList.append(
            {"tbl_title": tblTitle, "headers": tblHeader, "value": recordList[1:]}
        )


# This function creates a Text Fields list, which can then be used in an addendum file. The limit input is needed to determine if the text field input is too long to fit in the main form.
class myTextList:
    """
    Utility class for managing text fields that may exceed form space limits.
    
    This class handles text content that might be too long to fit in the main form
    by truncating it at a specified limit and storing the overflow text for use
    in addenda or continuation pages.
    """
    def __init__(self, text, limit, title):
        """
        Initialize text processing with truncation limits.
        
        Args:
            text (str): The text content to process and potentially truncate.
            limit (int): The character limit for the main form field.
            title (str): The title or identifier for the text field.
        """
        self.g(text, limit, title)

    def g(self, text, limit, title) -> None:
        """
        Process text for addendum generation by truncating if needed and storing overflow.

        Determines if the provided text exceeds the character limit and truncates it
        with an addendum notice if necessary. The original text is stored for inclusion
        in an addendum section if truncation occurs.

        Args:
            text (str): The text content to process for length.
            limit (int): The maximum character limit for the main text field.
            title (str): The title/label for this text field, used in the addendum.

        Note:
            Sets self.text_cutoff to the truncated text (with addendum notice if needed)
            and self.txtList to contain addendum data if truncation occurred.

        Example:
            >>> text_handler = myTextList("Very long text...", 100, "Description")
            >>> # If text > 100 chars, text_cutoff will end with " (See Addendum.)"
        """
        # 1. Adjust limit
        sLimit = (
            limit - 16
        )  # 16 gives the standard room for inserting " (See Addendum)"
        # 2. Evaluate and shorten a text/area variable
        need_addendum = len(text) > limit
        self.txtList = list()
        if need_addendum:
            self.text_cutoff = text[:sLimit] + " (See Addendum.)"
            # 3. Store the cutoff variable and its lable in txtFieldsList, whitch is referenced in the addendum file.
            self.txtList.append({"text_title": title, "value": text})
        else:
            self.text_cutoff = text


# Function safe_json2 is a revision of Jonathan's function safe_json - mainly to change the date format from string to date.
import types
import datetime
import decimal
import re
import json
from typing import Any

TypeType = type(type(None))


def safe_json2(the_object, level=0, is_key=False) -> Any:
    """
    Convert Python objects to JSON-serializable format with enhanced date handling.

    A revision of the safe_json function that converts complex Python objects into
    formats that can be safely serialized to JSON. Handles datetime objects by
    converting them to formatted date strings (MM/DD/YYYY format) rather than
    ISO strings.

    Args:
        the_object: The Python object to convert to a JSON-serializable format.
        level (int, optional): Current recursion depth to prevent infinite loops.
            Defaults to 0.
        is_key (bool, optional): Whether this object is being used as a dictionary key.
            Defaults to False.

    Returns:
        A JSON-serializable representation of the input object. Returns "None" for
        keys or None for values when objects cannot be serialized and recursion
        limit is exceeded.

    Example:
        >>> import datetime
        >>> obj = {"date": datetime.datetime(2023, 12, 25)}
        >>> safe_json2(obj)
        {"date": "12/25/2023"}
    """
    if level > 20:
        return "None" if is_key else None
    if isinstance(the_object, (str, bool, int, float)):
        return the_object
    if isinstance(the_object, list):
        return [safe_json2(x, level=level + 1) for x in the_object]
    if isinstance(the_object, dict):
        new_dict = dict()
        used_string = False
        used_non_string = False
        for key, value in the_object.items():
            the_key = safe_json2(key, level=level + 1, is_key=True)
            if isinstance(the_key, str):
                used_string = True
            else:
                used_non_string = True
            new_dict[the_key] = safe_json2(value, level=level + 1)
        if used_non_string and used_string:
            corrected_dict = dict()
            for key, value in new_dict.items():
                corrected_dict[str(key)] = value
            return corrected_dict
        return new_dict
    if isinstance(the_object, set):
        new_list = list()
        for sub_object in the_object:
            new_list.append(safe_json2(sub_object, level=level + 1))
        return new_list

    if isinstance(the_object, datetime.datetime):
        # serial = the_object.date()
        serial = the_object.date().strftime("%m/%d/%Y")
        return serial
    if isinstance(the_object, datetime.time):
        serial = the_object.isoformat()
        return serial
    if isinstance(the_object, decimal.Decimal):
        return float(the_object)

    from docassemble.base.core import DAObject

    if isinstance(the_object, DAObject):
        new_dict = dict()
        new_dict["_class"] = type_name(the_object)
        if (
            the_object.__class__.__name__ == "DALazyTemplate"
            or the_object.__class__.__name__ == "DALazyTableTemplate"
        ):
            if hasattr(the_object, "instanceName"):
                new_dict["instanceName"] = the_object.instanceName
            return new_dict
        for key, data in the_object.__dict__.items():
            if key in ["has_nonrandom_instance_name", "attrList"]:
                continue
            new_dict[safe_json2(key, level=level + 1, is_key=True)] = safe_json2(
                data, level=level + 1
            )
        return new_dict
    try:
        json.dumps(the_object)
    except:
        return "None" if is_key else None
    return the_object


def type_name(the_object) -> str:
    """
    Extract the class name from a Python object's type string representation.

    Parses the string representation of an object's type to extract just the
    class name, removing the surrounding type syntax.

    Args:
        the_object: Any Python object whose type name should be extracted.

    Returns:
        str: The class name of the object, or the full type string if parsing fails.

    Example:
        >>> type_name("hello")
        'str'
        >>> type_name([1, 2, 3])
        'list'
    """
    name = str(type(the_object))
    m = re.search(r"\'(.*)\'", name)
    if m:
        return m.group(1)
    return name
