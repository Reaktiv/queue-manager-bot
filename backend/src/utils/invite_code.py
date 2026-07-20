"""
Guruh uchun noyob taklif kodini generatsiya qilish.
"""

import secrets
import string

_ALPHABET = string.ascii_uppercase + string.digits
# Chalkashtiruvchi belgilarni chiqarib tashlaymiz (0/O, 1/I)
_ALPHABET = _ALPHABET.translate(str.maketrans("", "", "0O1I"))


def generate_invite_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
