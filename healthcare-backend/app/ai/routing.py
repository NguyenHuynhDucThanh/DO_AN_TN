"""Deterministic top-level routing; Gemini still selects a concrete business tool."""

from enum import StrEnum

from app.ai.risk.service import RiskAlertService


class ChatRoute(StrEnum):
    KNOWLEDGE = "KNOWLEDGE"
    BUSINESS_LOOKUP = "BUSINESS_LOOKUP"
    BOOKING = "BOOKING"
    HANDOFF = "HANDOFF"


class ChatIntentRouter:
    HANDOFF_MARKERS = (
        "nhan vien",
        "nguoi ho tro",
        "chuyen ho tro",
        "gap nguoi",
        "tu van vien",
    )
    BOOKING_MARKERS = (
        "dat lich",
        "dat kham",
        "chon slot",
        "xac nhan lich",
        "hen kham",
    )
    BUSINESS_MARKERS = (
        "bac si",
        "chuyen khoa",
        "lich lam viec",
        "lich kham",
        "slot",
        "khung gio",
        "gio trong",
        "con lich",
    )

    def route(self, message: str) -> ChatRoute:
        text = RiskAlertService.normalize(message)
        if any(marker in text for marker in self.HANDOFF_MARKERS):
            return ChatRoute.HANDOFF
        if any(marker in text for marker in self.BOOKING_MARKERS):
            return ChatRoute.BOOKING
        if any(marker in text for marker in self.BUSINESS_MARKERS):
            return ChatRoute.BUSINESS_LOOKUP
        return ChatRoute.KNOWLEDGE

