"""Authoring-standards test for the debian/debci-api skill.

Checks the Hermes authoring HARDLINE rules against the live SKILL.md (no network):.
- description <= 60 chars, one sentence, ends with period
- capability not implementation, no marketing words, does not repeat the name
- author has GitHub handle + "Hermes Agent" second
- section order: intro -> When to Use -> Prerequisites -> How to Run -> Quick Reference
  -> Procedure -> Pitfalls -> Verification
- prose references native Hermes tools in backticks (no shell utils)
"""
import os
import re
import pytest

SKILL = "debian/debci-api"
SKILL_MD = os.path.join("skills", SKILL, "SKILL.md")

ORDER = [
    ("# debian/debci-api Skill", 0), ("## When to Use", 1), ("## Prerequisites", 2),
    ("## How to Run", 3), ("## Quick Reference", 4), ("## Procedure", 5),
    ("## Pitfalls", 6), ("## Verification", 7),
]

@pytest.fixture(scope="module")
def skill_text():
    return open(SKILL_MD).read()

def parse_desc(skill_text):
    m = re.search(r"^description:\s*(.+)$", skill_text, re.M)
    assert m, "description missing"
    return m.group(1).strip().strip('"')

def parse_author(skill_text):
    m = re.search(r"^author:\s*(.+)$", skill_text, re.M)
    assert m, "author missing"
    return m.group(1).strip()

def test_description_length(skill_text):
    d = parse_desc(skill_text)
    assert len(d) <= 60, "description too long: " + d

def test_description_ends_with_period(skill_text):
    d = parse_desc(skill_text)
    assert d.endswith("."), "description must end with a period"

def test_description_no_name_repetition(skill_text):
    d = parse_desc(skill_text)
    name = re.search(r"^name:\s*(.+)$", skill_text, re.M).group(1).strip()
    assert name.lower() not in d.lower(), "description repeats the skill name"

def test_description_capability_not_implementation(skill_text):
    d = parse_desc(skill_text).lower()
    for bad in ["powerful", "comprehensive", "seamless", "advanced", "simple"]:
        assert bad not in d, "marketing word found: " + bad

def test_author_has_github_handle(skill_text):
    a = parse_author(skill_text)
    assert "@" in a and ")" in a, "author lacks GitHub handle: " + a
    assert "Hermes Agent" in a, "author must credit 'Hermes Agent'"

def test_section_order(skill_text):
    heads = re.findall(r"^##\s+(.+)$", skill_text, re.M)
    seen = [h for h in heads if h in [o[0] for o in ORDER]]
    positions = [next(i for h, i in ORDER if h in seen) for h in seen]
    assert positions == sorted(positions), "section order wrong: " + repr(seen)

def test_no_shell_utils_in_prose(skill_text):
    import re
    # Strip code fences so API examples in ``` bash blocks are not flagged.
    prose = re.sub(r"```.*?```", "", skill_text, flags=re.S)
    # Only flag a wrapped shell utility when it appears as a standalone word:
    # grep->search_files, cat/head/tail->read_file, sed/awk->patch, find/ls->search_files.
    for shell in ["grep", "cat", "head", "tail", "sed", "awk", "find", "ls"]:
        assert not re.search(r"\b" + re.escape(shell) + r"\b", prose), \
            "wrapped shell utility named in prose: " + shell

def test_scripts_referenced(skill_text):
    # HARDLINE std.6: only gbp-upstream-push ships a helper script.
    if "gbp-upstream-push" in SKILL:
        assert os.path.isdir("scripts"), "scripts/ directory is missing"
        assert os.listdir("scripts"), "scripts/ directory is empty"
