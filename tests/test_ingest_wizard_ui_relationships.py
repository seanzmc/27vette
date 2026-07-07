from pathlib import Path
import re


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")


def _source() -> str:
    return WIZARD_JS.read_text(encoding="utf-8")


def test_relationship_authoring_exposes_only_workbook_safe_rule_choices() -> None:
    source = _source()
    block = re.search(r"const RELATIONSHIP_KIND_CHOICES = \[(.*?)\];", source, re.S)
    assert block, "RELATIONSHIP_KIND_CHOICES block not found"
    values = re.findall(r'value: "([^"]+)"', block.group(1))
    assert values == ["requires", "includes", "not_available_with"]
    for stale in ("deletes", "replaces", "upgradeable_to", "other"):
        assert f'value: "{stale}"' not in block.group(1)


def test_relationship_form_removes_generic_question_and_resolution_controls() -> None:
    source = _source()
    assert "group-product-decision" not in source
    assert 'const resolutionControl = lane === "relationship" ? ""' in source
    assert 'Save relationship' in source
    assert 'record as business question' not in source.lower()


def test_relationship_hint_aliases_normalize_to_safe_rule_choices() -> None:
    source = _source()
    alias_block = re.search(r"const RELATIONSHIP_KIND_ALIASES = \{(.*?)\};", source, re.S)
    assert alias_block, "RELATIONSHIP_KIND_ALIASES block not found"
    aliases = dict(re.findall(r'(\w+): "([^"]+)"', alias_block.group(1)))
    assert aliases == {
        "only_available_with": "requires",
        "requires_additional_equipment": "requires",
        "included_with": "includes",
    }
    assert "setRelationshipKind(hint.dataset.kind)" in source
    assert "selectedRelationshipKind()" in source
