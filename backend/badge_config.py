"""
Badge metadata and logic for IBM Z Xplore learning path.
"""

FUNDAMENTALS = ["VSC1", "FILES1", "JCL1", "USS1", "CODE1", "REXX1", "WRAPUP"]
CONCEPTS_IDS = ["IBM_Z_PRACTITIONERS", "ENTERPRISE_SYSTEMS"]
ADVANCED_IDS = ["ZCLI1", "LNX2", "USS2", "PDS2", "PDS1"]
ALLSTAR_IDS = ["LNX1", "SQL1", "JCL2"]

BADGES: dict[str, dict] = {
    # ── Fundamentals ────────────────────────────────────────────────────────
    "VSC1": {
        "title": "Visual Studio Code",
        "type": "Fundamentals",
        "points": 15,
        "pdf": "VSC1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "FILES1": {
        "title": "Files",
        "type": "Fundamentals",
        "points": 18,
        "pdf": "FILES1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "JCL1": {
        "title": "JCL Basics",
        "type": "Fundamentals",
        "points": 18,
        "pdf": "JCL1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "USS1": {
        "title": "Unix System Services Basics",
        "type": "Fundamentals",
        "points": 18,
        "pdf": "USS1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "CODE1": {
        "title": "Coding Basics",
        "type": "Fundamentals",
        "points": 20,
        "pdf": "CODE1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "REXX1": {
        "title": "REXX Basics",
        "type": "Fundamentals",
        "points": 20,
        "pdf": "REXX1.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    "WRAPUP": {
        "title": "Wrap Up",
        "type": "Fundamentals",
        "points": 20,
        "pdf": "WRAPUP.pdf",
        "required_for": ["CONCEPTS_COMPLETION"],
    },
    # ── Concepts ────────────────────────────────────────────────────────────
    "IBM_Z_PRACTITIONERS": {
        "title": "IBM Z Practitioners",
        "type": "Concepts",
        "points": 14,
        "pdf": "IBM Z Practitioners.pdf",
        "required_for": ["CONCEPTS_COMPLETION", "ADVANCED_COMPLETION"],
    },
    "ENTERPRISE_SYSTEMS": {
        "title": "Enterprise Systems",
        "type": "Concepts",
        "points": 14,
        "pdf": "Enterprise Systems.pdf",
        "required_for": ["CONCEPTS_COMPLETION", "ADVANCED_COMPLETION"],
    },
    # ── Advanced ────────────────────────────────────────────────────────────
    "ZCLI1": {
        "title": "Z CLI Basics",
        "type": "Advanced",
        "points": 30,
        "pdf": "ZCLI1.pdf",
        "required_for": ["ADVANCED_COMPLETION"],
    },
    "LNX2": {
        "title": "Linux Advanced",
        "type": "Advanced",
        "points": 30,
        "pdf": "LNX2.pdf",
        "required_for": ["ADVANCED_COMPLETION"],
    },
    "USS2": {
        "title": "Unix System Services Advanced",
        "type": "Advanced",
        "points": 30,
        "pdf": "USS2.pdf",
        "required_for": ["ADVANCED_COMPLETION"],
    },
    "PDS2": {
        "title": "Partitioned Data Sets Advanced",
        "type": "Advanced",
        "points": 31,
        "pdf": "PDS2.pdf",
        "required_for": ["ADVANCED_COMPLETION"],
    },
    "PDS1": {
        "title": "Partitioned Data Sets Basics",
        "type": "Advanced",
        "points": 31,
        "pdf": "PDS1.pdf",
        "required_for": ["ADVANCED_COMPLETION"],
    },
    # ── AllStar ─────────────────────────────────────────────────────────────
    "LNX1": {
        "title": "Linux Basics",
        "type": "AllStar",
        "points": 30,
        "pdf": "LNX1.pdf",
        "required_for": ["ADVANCED_COMPLETION", "ALLSTAR_COMPLETION"],
    },
    "SQL1": {
        "title": "SQL Basics",
        "type": "AllStar",
        "points": 30,
        "pdf": "SQL1.pdf",
        "required_for": ["ADVANCED_COMPLETION", "ALLSTAR_COMPLETION"],
    },
    "JCL2": {
        "title": "JCL Advanced",
        "type": "AllStar",
        "points": 31,
        "pdf": "JCL2.pdf",
        "required_for": ["ADVANCED_COMPLETION", "ALLSTAR_COMPLETION"],
    },
}


def check_concepts_badge(completed: list[str]) -> bool:
    """
    Unlock condition for Concepts completion:
      - All 7 Fundamentals badges earned
      - At least 2 Concepts badges earned
    """
    has_all_fundamentals = all(b in completed for b in FUNDAMENTALS)
    concepts_done = sum(1 for b in CONCEPTS_IDS if b in completed)
    return has_all_fundamentals and concepts_done >= 2


def check_advanced_badge(completed: list[str]) -> bool:
    """
    Unlock condition for Advanced completion:
      - At least 5 badges from the combined Advanced + AllStar pool
    """
    advanced_allstar = ADVANCED_IDS + ALLSTAR_IDS
    done = sum(1 for b in advanced_allstar if b in completed)
    return done >= 5


def suggest_next_badge(completed: list[str]) -> list[str]:
    """
    Suggest the next badge(s) to pursue based on what has been completed.

    Priority order:
      1. Remaining Fundamentals (complete the foundation first)
      2. Remaining Concepts (if all Fundamentals done, push toward 2 Concepts)
      3. Advanced / AllStar (highest-points badges first)

    Returns a list of up to 3 suggested badge IDs.
    """
    completed_set = set(completed)

    # 1. Incomplete Fundamentals — preserve learning-path order
    remaining_fundamentals = [b for b in FUNDAMENTALS if b not in completed_set]
    if remaining_fundamentals:
        return remaining_fundamentals[:3]

    # 2. Concepts — need at least 2; suggest uncompleted ones first
    concepts_done = [b for b in CONCEPTS_IDS if b in completed_set]
    if len(concepts_done) < 2:
        remaining_concepts = [b for b in CONCEPTS_IDS if b not in completed_set]
        return remaining_concepts[: 2 - len(concepts_done)]

    # 3. Advanced + AllStar — sort by points descending to maximise score gain
    advanced_allstar = ADVANCED_IDS + ALLSTAR_IDS
    remaining = [b for b in advanced_allstar if b not in completed_set]
    remaining_sorted = sorted(remaining, key=lambda b: BADGES[b]["points"], reverse=True)
    return remaining_sorted[:3]
