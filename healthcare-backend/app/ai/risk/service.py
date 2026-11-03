"""Pure rule engine: no Gemini, database, MedicalRecord, or free-form diagnosis."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.ai.risk.rules import CURRENT_EVENT_MARKERS, EDUCATIONAL_MARKERS, RISK_RULES


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    rule_codes: tuple[str, ...]
    categories: tuple[str, ...]


class RiskAlertService:
    @staticmethod
    def normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFD", value.casefold())
        without_marks = "".join(
            character for character in decomposed if unicodedata.category(character) != "Mn"
        ).replace("đ", "d")
        return re.sub(r"\s+", " ", without_marks).strip()

    @staticmethod
    def _is_negated(text: str, start: int, match_text: str) -> bool:
        # "không thở được" is itself an emergency phrase, not a negation.
        if match_text.startswith(("khong tho duoc", "khong danh thuc duoc")):
            return False
        prefix = text[max(0, start - 28):start]
        return re.search(r"\b(?:khong|chua)\b(?:\W+\w+){0,3}\W*$", prefix) is not None

    def assess(self, message: str) -> RiskAssessment | None:
        text = self.normalize(message)
        educational = any(marker in text for marker in EDUCATIONAL_MARKERS) or bool(
            re.search(
                r"\b(?:dau hieu|trieu chung|thong tin|bai viet|vi du|tim hieu|cach nhan biet)\b"
                r".*\b(?:la gi|nhu the nao|ve)\b",
                text,
            )
        ) or bool(re.search(r"\b(?:khong tho duoc|bat tinh|ngo doc|tu tu) la gi\b", text))
        current_event = any(marker in text for marker in CURRENT_EVENT_MARKERS)
        if educational and not current_event:
            return None

        matched_codes: list[str] = []
        matched_categories: list[str] = []
        for rule in RISK_RULES:
            for pattern in rule.patterns:
                match = re.search(pattern, text)
                if match is None or self._is_negated(text, match.start(), match.group(0)):
                    continue
                matched_codes.append(rule.code)
                matched_categories.append(rule.category)
                break
        if not matched_codes:
            return None
        return RiskAssessment(tuple(matched_codes), tuple(matched_categories))

