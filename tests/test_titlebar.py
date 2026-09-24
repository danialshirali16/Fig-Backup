import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from figma_backup.app import _position_titlebar_buttons


class TitlebarTests(unittest.TestCase):
    def test_button_insets_survive_resize_without_accumulating(self):
        class Button:
            def __init__(self, x, y, parent):
                self.rect = SimpleNamespace(
                    origin=SimpleNamespace(x=x, y=y),
                    size=SimpleNamespace(width=14, height=14),
                )
                self.parent = parent

            def frame(self):
                return self.rect

            def superview(self):
                return self.parent

            def setFrameOrigin_(self, point):
                self.rect.origin.x, self.rect.origin.y = point

        parent = SimpleNamespace(
            bounds=lambda: SimpleNamespace(
                origin=SimpleNamespace(x=0, y=0),
                size=SimpleNamespace(width=960, height=48),
            ),
            isFlipped=lambda: False,
        )
        buttons = {kind: Button(x, 27, parent) for kind, x in enumerate((14, 34, 54))}
        native = SimpleNamespace(standardWindowButton_=buttons.__getitem__)
        window = SimpleNamespace(native=native)
        appkit = SimpleNamespace(
            NSWindowCloseButton=0,
            NSWindowMiniaturizeButton=1,
            NSWindowZoomButton=2,
            NSMakePoint=lambda x, y: (x, y),
        )

        with patch.dict(sys.modules, {"AppKit": appkit}):
            _position_titlebar_buttons(window)
            self.assertEqual([(b.frame().origin.x, b.frame().origin.y)
                              for b in buttons.values()], [(20, 19), (40, 19), (60, 19)])

            # A resize may leave the custom frames alone or reset them. Both
            # cases must return to the same top-left insets.
            _position_titlebar_buttons(window)
            self.assertEqual([(b.frame().origin.x, b.frame().origin.y)
                              for b in buttons.values()], [(20, 19), (40, 19), (60, 19)])
            parent.bounds = lambda: SimpleNamespace(
                origin=SimpleNamespace(x=0, y=0),
                size=SimpleNamespace(width=1200, height=60),
            )
            for kind, button in buttons.items():
                button.setFrameOrigin_((14 + kind * 20, 39))
            _position_titlebar_buttons(window)
            self.assertEqual([(b.frame().origin.x, b.frame().origin.y)
                              for b in buttons.values()], [(20, 31), (40, 31), (60, 31)])


if __name__ == "__main__":
    unittest.main()
