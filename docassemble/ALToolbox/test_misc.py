import re
import unittest
from unittest.mock import patch
from .misc import button_array, ButtonDict, true_values_with_other
import xml.etree.ElementTree as ET


class TestButtonArray(unittest.TestCase):
    def normalize_whitespace(self, s):
        return re.sub(r"\s+", " ", s)

    @patch("docassemble.ALToolbox.misc.user_has_privilege", return_value=False)
    def test_button_array_generates_correct_html(self, mock_privilege):
        buttons = [
            ButtonDict(name="Button 1", image="image1", url="url1"),
            ButtonDict(name="Button 2", image="image2", url="url2"),
        ]

        # Just check it is valid HTML
        button_array_html = button_array(buttons)
        try:
            ET.fromstring(button_array_html)
            # If the parsing succeeds, the HTML is well-formed
        except ET.ParseError:
            # If the parsing fails, the HTML is not well-formed
            self.fail("button_array generated malformed HTML")
        self.assertIn("Button 1", button_array_html)
        self.assertIn("Button 2", button_array_html)

    @patch("docassemble.ALToolbox.misc.user_has_privilege", return_value=False)
    def test_button_array_filters_by_privilege(self, mock_privilege):
        buttons = [
            ButtonDict(name="Button 1", image="image1", url="url1", privilege="admin"),
            ButtonDict(name="Button 2", image="image2", url="url2"),
        ]
        self.assertNotIn("Button 1", button_array(buttons))


if __name__ == "__main__":
    unittest.main()
