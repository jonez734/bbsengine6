"""FormItemTextbox carries a label, a name and a mask; a Form keeps its items in order.

The mask rule is the one inputpassword uses: "" (show nothing, the default), a single character, or None (show the
text, for accessibility). Any other value is refused.
"""

import unittest

from bbsengine6.form import Form, FormItemTextbox


class TestTextboxFields(unittest.TestCase):
    def test_a_textbox_carries_its_label_and_name(self):
        box = FormItemTextbox(label="moniker:", name="moniker")
        self.assertEqual((box.label, box.name), ("moniker:", "moniker"))
        self.assertEqual(box.kind, "TEXT")

    def test_the_default_mask_shows_nothing(self):
        self.assertEqual(FormItemTextbox(label="password:", name="password").mask, "")

    def test_a_single_character_mask_is_kept(self):
        self.assertEqual(FormItemTextbox(label="password:", name="password", mask="*").mask, "*")

    def test_none_is_kept_for_accessibility(self):
        self.assertIsNone(FormItemTextbox(label="password:", name="password", mask=None).mask)

    def test_a_longer_mask_is_refused_like_inputpassword(self):
        with self.assertRaises(ValueError):
            FormItemTextbox(label="password:", name="password", mask="XX")


class TestFormOrder(unittest.TestCase):
    def test_a_form_keeps_its_items_in_order(self):
        moniker = FormItemTextbox(label="moniker:", name="moniker")
        password = FormItemTextbox(label="password:", name="password", mask="")
        form = Form("zoid6 auth", [moniker, password])
        self.assertEqual(len(form), 2)
        self.assertIs(form[0], moniker)
        self.assertIs(form[1], password)
        self.assertEqual([item.name for item in form], ["moniker", "password"])


if __name__ == "__main__":
    unittest.main()
