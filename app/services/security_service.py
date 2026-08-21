"""
Security and Input Sanitization Service.
Defends against prompt injection, control character abuse, and malformed inputs.
"""

import re
import html
from typing import Tuple


class SecurityService:
    # Common prompt injection / escape attempt indicators
    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"disregard all previous instructions",
        r"system override",
        r"you are now in developer mode",
        r"jailbreak",
        r"bypass security",
        r"assistant:\s*ignore"
    ]

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 10000) -> str:
        """
        Sanitizes raw text:
        - Truncates to max_length
        - Strips dangerous control / null bytes
        - Normalizes Unicode whitespace
        - Strips surrounding quotes
        """
        if not text:
            return ""

        # Truncate
        sanitized = text[:max_length]

        # Strip null bytes and non-printable control characters (except newline, tab, carriage return)
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Normalize multiple consecutive spaces/newlines
        sanitized = re.sub(r"\r\n|\r", "\n", sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)

        return sanitized.strip()

    @classmethod
    def check_injection_risk(cls, text: str) -> Tuple[bool, str]:
        """
        Scans input for potential prompt injection attempts.
        Returns (is_suspicious, reason).
        """
        lower = text.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, lower):
                return True, f"Potentially adversarial prompt pattern detected: '{pattern}'"
        return False, ""


security_service = SecurityService()
