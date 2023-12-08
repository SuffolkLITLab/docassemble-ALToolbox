import re
import unittest
from unittest.mock import patch
from .misc import button_array, ButtonDict, safe_get_config
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


EMPTY_INTERVIEW_LIST = {
  "enable answer sets": True,
  "interview list": {}
}
NONE_INTERVIEW_LIST = {
  "enable answer sets": True,
  "interview list": None
}
OKAY_INTERVIEW_LIST = {
  "enable answer sets": True,
  "interview list": {
    "logo title row 1": "Test"
  }
}

class TestSafeGetConfig(unittest.TestCase):
    @patch("docassemble.ALToolbox.misc.get_config", return_value=None)
    def test_safe_get_config_with_no_assembly_line(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list"), None)

    @patch("docassemble.ALToolbox.misc.get_config", return_value={})
    def test_safe_get_config_with_empty_assembly_line(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list"), None)

    @patch("docassemble.ALToolbox.misc.get_config", return_value=EMPTY_INTERVIEW_LIST)
    def test_safe_get_config_with_interview_list(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list"), {})

    @patch("docassemble.ALToolbox.misc.get_config", return_value=NONE_INTERVIEW_LIST)
    def test_safe_get_config_with_none_interview_list(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list"), None)

    @patch("docassemble.ALToolbox.misc.get_config", return_value=OKAY_INTERVIEW_LIST)
    def test_safe_get_config_with_okay_interview_list(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list", "logo title row 1"), "Test")

    @patch("docassemble.ALToolbox.misc.get_config", return_value=OKAY_INTERVIEW_LIST)
    def test_safe_get_config_with_bad_user_params(self, mock_config):
        self.assertEqual(safe_get_config("assembly line", "interview list", 1), None)


if __name__ == "__main__":
    unittest.main()
