import re
import unittest

from mochi_pet import HYDRATION_REMINDER_TEXT, MochiPet


CHINESE_CHARACTER = re.compile(r"[\u3400-\u9fff]")


class UiCopyTests(unittest.TestCase):
    def test_automatic_pet_messages_are_chinese(self):
        messages = (*MochiPet.messages, *MochiPet.happy_messages, HYDRATION_REMINDER_TEXT)
        self.assertTrue(messages)
        for message in messages:
            self.assertRegex(message, CHINESE_CHARACTER)

    def test_normal_message_resets_hydration_emphasis(self):
        pet = object.__new__(MochiPet)
        pet._set_message(HYDRATION_REMINDER_TEXT, 12.0, emphasized=True, now=10.0)
        self.assertTrue(pet.message_emphasis)
        self.assertEqual(pet.message_until, 22.0)

        pet._set_message("已经喝水啦！", 3.0, now=20.0)
        self.assertFalse(pet.message_emphasis)
        self.assertEqual(pet.message_until, 23.0)


if __name__ == "__main__":
    unittest.main()
