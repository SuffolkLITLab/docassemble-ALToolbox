# do not pre-load

import json
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from .misc import review_widget


class WidgetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") in ("al-thumbs-widget-up", "al-thumbs-widget-down"):
            self.controls[attrs["id"]] = (tag, attrs)


class TestReviewWidget(unittest.TestCase):
    def controls(self, **kwargs):
        parser = WidgetParser()
        parser.feed(review_widget(**kwargs))
        return parser.controls

    def test_thumbs_are_non_submit_buttons(self):
        controls = self.controls(up_action="helpful", down_action="unhelpful")
        self.assertEqual(len(controls), 2)
        for control, action in (("up", "helpful"), ("down", "unhelpful")):
            tag, attrs = controls[f"al-thumbs-widget-{control}"]
            self.assertEqual(tag, "button")
            self.assertEqual(attrs["type"], "button")
            self.assertNotIn("href", attrs)
            self.assertEqual(attrs["onclick"], f'altoolbox_thumbs_{control}_send("{action}", false)')
            self.assertIn("btn-info", attrs["class"])

    def test_handlers_keep_the_optional_review_stage_and_escape_actions(self):
        action = 'feedback["helpful"]'
        controls = self.controls(up_action=action, down_action="unhelpful", review_action="review")
        self.assertEqual(controls["al-thumbs-widget-up"][1]["onclick"],
                         f"altoolbox_thumbs_up_send({json.dumps(action)}, true)")
        self.assertEqual(controls["al-thumbs-widget-down"][1]["onclick"],
                         'altoolbox_thumbs_down_send("unhelpful", true)')

    @patch("docassemble.ALToolbox.misc.word", side_effect=lambda text: f'Traducido "{text}"')
    def test_accessible_labels_remain_translated(self, mock_word):
        controls = self.controls(up_action="helpful", down_action="unhelpful")
        self.assertEqual(controls["al-thumbs-widget-up"][1]["aria-label"], 'Traducido "Thumbs up"')
        self.assertEqual(controls["al-thumbs-widget-down"][1]["aria-label"], 'Traducido "Thumbs down"')
