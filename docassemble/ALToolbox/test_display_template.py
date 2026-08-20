import unittest
from types import SimpleNamespace

from .display_template import display_template


class TestDisplayTemplate(unittest.TestCase):
    def setUp(self):
        self.template = SimpleNamespace(
            instanceName="test-template",
            subject="Subject",
            subject_as_html=lambda trim: "Subject",
            content_as_html=lambda: "Content",
        )

    def test_subject_defaults_to_h2(self):
        html = display_template(self.template)

        self.assertIn('<h2 class="subject"', html)
        self.assertNotIn("<h3", html)

    def test_subject_heading_level_can_be_customized(self):
        html = display_template(self.template, h_level=4)

        self.assertIn('<h4 class="subject"', html)
        self.assertNotIn("<h2", html)

    def test_subject_heading_level_must_be_between_one_and_six(self):
        for h_level in (0, 7, "2"):
            with self.subTest(h_level=h_level):
                with self.assertRaises(ValueError):
                    display_template(self.template, h_level=h_level)


if __name__ == "__main__":
    unittest.main()
