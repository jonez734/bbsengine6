class FormItem:
    def __init__(self):
        self.kind = "BASE"


class FormItemCheckbox(FormItem):
    def __init__(self):
        super().__init__()
        self.kind = "CHECKBOX"


class FormItemRadioButton(FormItem):
    def __init__(self):
        super().__init__()
        self.kind = "RADIO"
        self.value = None


def check_mask(mask):
    """A textbox mask follows the inputpassword rule: "" (show nothing), one character, or None (show the text).

    Any other value raises ValueError, so a password can never be shown by accident.
    """
    if mask is not None and len(mask) > 1:
        raise ValueError(f"mask must be '', None, or one character, not {mask!r}")
    return mask


class FormItemTextbox(FormItem):
    """A labelled text field. ``mask`` defaults to "" (show nothing), so a password is hidden unless asked otherwise."""

    def __init__(self, label: str = "", name: str = "", mask=""):
        super().__init__()
        self.kind = "TEXT"
        self.label = label
        self.name = name
        self.mask = check_mask(mask)


# @since 20230617 copied from bbsengine5
class Form(object):
    def __init__(self, title, items, args=None):
        self.items = items
        self.title = title
        self.args = args

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]
