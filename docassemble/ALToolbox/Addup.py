# Add up numeric field values from a DAList object.
from docassemble.base.util import DAValidationError, word

__all__ = ["Addup"]


class Addup:
    """
    Utility class for calculating sums of numeric fields across DAList objects.

    This class provides functionality to sum specific numeric fields from all
    items in a Docassemble DAList, which is useful for financial calculations
    and data aggregation in legal document automation.
    """

    def __init__(self, listName, varName):
        """
        Initialize the Addup calculator and compute the sum immediately.

        Args:
            self: The instance being initialized.
            listName: A DAList object containing items with numeric fields.
            varName (str): The name of the field to sum across all list items.
        """
        self.g(listName, varName)

    def g(self, listName, varName) -> float:
        """
        Calculate the sum of a specific numeric field across all items in a DAList.

        Iterates through each item in the provided DAList, extracts the specified
        field value, and adds all values together. Raises an error if the sum is 0,
        which indicates the field was not found or contained no numeric values.

        Args:
            listName: A DAList object containing items with numeric fields.
            varName (str): The name of the field to sum across all list items.

        Returns:
            float: The sum of all values for the specified field.

        Raises:
            DAValidationError: If the sum is 0, indicating the field was not found
                or contained no numeric values.

        Example:
            >>> addup = Addup(income_list, "monthly_amount")
            >>> # Returns sum of monthly_amount fields from all items in income_list
        """
        self.sum = 0
        for w in listName:
            my_dict = w.as_serializable()
            for key, val in my_dict.items():
                if key == varName:
                    self.sum += val
        if self.sum == 0:
            msg = (
                "Make sure your field '"
                + varName
                + "' is spelled correctly and is numeric."
            )
            raise DAValidationError(msg)
        else:
            return self.sum
