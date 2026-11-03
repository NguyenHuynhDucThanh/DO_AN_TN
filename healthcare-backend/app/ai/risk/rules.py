"""High-specificity synthetic/demo scenarios required by SRS FR-CHAT-06."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskRule:
    code: str
    category: str
    patterns: tuple[str, ...]


RISK_RULES = (
    RiskRule(
        "RISK-RESPIRATORY",
        "severe_breathing",
        (
            r"\bkhong tho duoc\b",
            r"\bngung tho\b",
            r"\bkho tho du doi\b",
            r"\bkho tho kem tim tai\b",
        ),
    ),
    RiskRule(
        "RISK-CHEST",
        "severe_chest_pain",
        (
            r"\bdau (?:that )?nguc du doi\b",
            r"\bdau (?:that )?nguc (?:kem|va) kho tho\b",
            r"\bdau nguc (?:kem|va) va mo hoi\b",
        ),
    ),
    RiskRule(
        "RISK-STROKE",
        "stroke_signs",
        (
            r"\bliet nua nguoi\b",
            r"\bye[u]? nua nguoi dot ngot\b",
            r"\bnoi ngong dot ngot\b",
            r"\bmeo mieng (?:kem|va) (?:yeu|liet)\b",
        ),
    ),
    RiskRule(
        "RISK-BLEEDING",
        "severe_bleeding",
        (
            r"\bchay mau khong cam\b",
            r"\bchay mau khong ngung\b",
            r"\bchay mau rat nhieu\b",
            r"\bmat mau nhieu\b",
        ),
    ),
    RiskRule(
        "RISK-CONSCIOUSNESS",
        "unconscious_or_seizure",
        (
            r"\bbat tinh\b",
            r"\bhon me\b",
            r"\bkhong danh thuc duoc\b",
            r"\bco giat (?:keo dai|lien tuc)\b",
        ),
    ),
    RiskRule(
        "RISK-POISONING",
        "poisoning_or_overdose",
        (
            r"\bngo doc\b",
            r"\bqua lieu thuoc\b",
            r"\buong nham .{0,30} qua lieu\b",
        ),
    ),
    RiskRule(
        "RISK-SELF-HARM",
        "imminent_self_harm",
        (
            r"\bmuon tu tu\b",
            r"\bsap tu tu\b",
            r"\bmuon tu lam hai (?:minh|ban than)\b",
            r"\bsap lam hai ban than\b",
        ),
    ),
)

EDUCATIONAL_MARKERS = (
    "dau hieu la gi",
    "trieu chung la gi",
    "cach nhan biet",
    "tim hieu ve",
    "bai viet ve",
    "vi du ve",
    "thong tin ve",
)

CURRENT_EVENT_MARKERS = (
    "hien tai",
    "luc nay",
    "bay gio",
    "dang bi",
    "dang chay mau",
    "dang co giat",
    "vua bi",
)

