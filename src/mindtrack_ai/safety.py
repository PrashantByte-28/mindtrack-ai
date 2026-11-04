import re

CRISIS_MESSAGE = """
I'm really sorry you're going through something so difficult. You deserve
support, and you don't have to face this alone.

If you might act on thoughts of suicide or hurt yourself right now, please
contact your local emergency services or go to the nearest emergency
department. If possible, reach out to someone you trust and ask them to
stay with you.

You can also contact a crisis support service in your country.

I'm an AI wellness companion, not an emergency service or a substitute
for professional mental healthcare.
""".strip()

# This is a lightweight keyword detector, not a clinical risk assessment.

RISK_PATTERNS = [
    # Explicit suicide-related language
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\btake my own life\b",
    r"\bcommit suicide\b",
    r"\bsuicid(?:e|al)\b",
    r"\bwant to die\b",
    r"\bwish i (?:was|were) dead\b",
    r"\bbetter off dead\b",

    # Self-harm and overdose
    r"\bhurt myself\b",
    r"\bharm myself\b",
    r"\bself[\s-]?harm\b",
    r"\bcut myself\b",
    r"\boverdose\b",

    # # Severe distress and hopelessness
    # r"\bcan't go on\b",
    # r"\bcannot go on\b",
    
]

# These phrases can indicate that a matching term is being denied.
NEGATION_PATTERNS = [
    r"\bdo not\b",
    r"\bdon't\b",
    r"\bnever\b",
    r"\bnot thinking about\b",
    r"\bnot planning to\b",
    r"\bwould not\b",
    r"\bwouldn't\b",
]

RISK_PHRASES = [
    "kill myself",
    "end my life",
    "suicide",
    "want to die",
    "hurt myself",
    "self harm",
    "self-harm",
]


def check_message_safety(message: str) -> bool:
    """
    Detect configured high-risk phrases.

    This is a basic heuristic, not a clinical risk assessment.
    Negation is considered only in the nearby part of the same clause.
    """
    if not isinstance(message, str) or not message.strip():
        return False

    normalized = message.lower().replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    for pattern in RISK_PATTERNS:
        for match in re.finditer(pattern, normalized):
            # Examine only nearby text before the matched phrase.
            prefix = normalized[max(0, match.start() - 60):match.start()]

            # Stop at punctuation or contrast/conjunction words so a
            # negation does not suppress a separate risk statement.
            clauses = re.split(
                r"[.!?;,]|\b(?:but|however|yet|although|though|and|or)\b",
                prefix,
            )
            nearby_context = clauses[-1].strip()

            if any(
                re.search(negation, nearby_context)
                for negation in NEGATION_PATTERNS
            ):
                continue

            return True

    return False