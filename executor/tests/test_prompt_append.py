import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.prompts.prompt_append import build_prompt_appendix


class PromptAppendixTests(unittest.TestCase):
    def test_office_assistant_policy_is_included(self) -> None:
        appendix = build_prompt_appendix(browser_enabled=False, memory_enabled=False)

        self.assertIn("Office assistant policy:", appendix)
        self.assertIn("Prefer deliverables under outputs/", appendix)
        self.assertIn("Prefer versioned outputs", appendix)
        self.assertIn("write helper code to hidden working files", appendix)

    def test_browser_note_is_appended_after_office_policy(self) -> None:
        appendix = build_prompt_appendix(browser_enabled=True, memory_enabled=False)

        self.assertIn("Office assistant policy:", appendix)
        self.assertIn("Browser capability note:", appendix)


if __name__ == "__main__":
    unittest.main()
