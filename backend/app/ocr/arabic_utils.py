import re
from typing import Optional, Tuple, Any

# Arabic to Western numeral mapping
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EAST_ARABIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
WESTERN_DIGITS = "0123456789"

ARABIC_TO_WESTERN_TABLE = str.maketrans(ARABIC_INDIC_DIGITS + EAST_ARABIC_DIGITS, WESTERN_DIGITS * 2)
WESTERN_TO_ARABIC_TABLE = str.maketrans(WESTERN_DIGITS, ARABIC_INDIC_DIGITS)

# Common Arabic decimal separators: '٫' (Arabic decimal separator U+066B), ',' and '.'
ARABIC_DECIMAL_SEP = "٫"
ARABIC_THOUSANDS_SEP = "٬"


def normalize_arabic_digits(text: str) -> str:
    """Convert Arabic-Indic numerals to standard Western numerals without changing Arabic letters."""
    if not text:
        return ""
    return text.translate(ARABIC_TO_WESTERN_TABLE)


def convert_western_to_arabic_digits(text: str) -> str:
    """Convert Western digits to Arabic-Indic digits."""
    if not text:
        return ""
    return text.translate(WESTERN_TO_ARABIC_TABLE)


def parse_arabic_number(text: str) -> Tuple[Optional[float], Optional[int], bool]:
    """Return float value, integer value, and whether text contains a number."""
    if not text:
        return None, None, False
    clean_text = _clean_number_text(text)
    match = re.search(r"[-+]?\d*\.?\d+", clean_text)
    if not match:
        return None, None, False

    num_str = match.group(0)
    try:
        if "." in num_str:
            f_val = float(num_str)
            return f_val, None, True
        else:
            i_val = int(num_str)
            return float(i_val), i_val, True
    except ValueError:
        return None, None, False


def _clean_number_text(text: str) -> str:
    clean_text = text.strip()
    clean_text = clean_text.replace(ARABIC_DECIMAL_SEP, ".")
    clean_text = clean_text.replace(ARABIC_THOUSANDS_SEP, "")
    clean_text = normalize_arabic_digits(clean_text)
    currency_pattern = r"(?:ر\.س|ريال|جنيه|درهم|د\.إ|دينار|USD|SAR|AED|EGP|\$|€|£)"
    return re.sub(currency_pattern, "", clean_text, flags=re.IGNORECASE).strip()


def is_arabic_text(text: str) -> bool:
    """Check if string contains Arabic characters (Unicode range U+0600-U+06FF)."""
    if not text:
        return False
    arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
    return bool(arabic_pattern.search(text))


def clean_arabic_string(text: str) -> str:
    """Safely cleans OCR artifacts like rogue control characters while preserving Arabic letters and punctuation."""
    if not text:
        return ""
    # Remove null bytes and non-printable control chars except newlines and tabs
    cleaned = "".join(ch for ch in text if ch in ("\n", "\t", "\r") or (ch.isprintable() and ord(ch) != 0))
    return cleaned.strip()
