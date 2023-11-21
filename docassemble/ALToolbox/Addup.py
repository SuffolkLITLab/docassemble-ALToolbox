# Add up numeric field values from a DAList object.
from docassemble.base.util import DAValidationError, word

__all__ = ["Addup"]


class Addup:
    def __init__(self, listName, varName):
        self.g(listName, varName)

    def g(self, listName, varName):
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
