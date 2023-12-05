import re
import unittest
from unittest.mock import patch
from .misc import button_array, ButtonDict

class TestButtonArray(unittest.TestCase):

    def normalize_whitespace(self, s):
        return re.sub(r'\s+', ' ', s)

    def test_button_array_generates_correct_html(self):
        buttons = [
            ButtonDict(name="Button 1", image="image1", url="url1"),
            ButtonDict(name="Button 2", image="image2", url="url2"),
        ]
        expected_html = self.normalize_whitespace(
            '<div class="da-button-set da-field-buttons ">'
            '<a class="btn btn-da btn-light btn-da btn-da-custom " href="url1">'
            '<i class="fa fa-image1"></i> Button 1'
            '</a>'
            '<a class="btn btn-da btn-light btn-da btn-da-custom " href="url2">'
            '<i class="fa fa-image2"></i> Button 2'
            '</a>'
            '</div>'
        )
        self.assertEqual(self.normalize_whitespace(button_array(buttons)), expected_html)

    @patch('.misc.user_has_privilege', return_value=False)
    def test_button_array_filters_by_privilege(self, mock_privilege):
        buttons = [
            ButtonDict(name="Button 1", image="image1", url="url1", privilege="admin"),
            ButtonDict(name="Button 2", image="image2", url="url2"),
        ]
        expected_html = self.normalize_whitespace(
            '<div class="da-button-set da-field-buttons ">'
            '<a class="btn btn-da btn-light btn-da btn-da-custom " href="url2">'
            '<i class="fa fa-image2"></i> Button 2'
            '</a>'
            '</div>'
        )
        self.assertEqual(self.normalize_whitespace(button_array(buttons)), expected_html)

if __name__ == '__main__':
    unittest.main()