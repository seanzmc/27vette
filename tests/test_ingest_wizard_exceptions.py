#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.canonical_rows import subject_id, subject_version  # noqa: E402
from corvette_form_generator.ingest.wizard.exceptions import (  # noqa: E402
    ALLOWED_DEFERRAL_KINDS,
    build_audit_event,
    build_resolution_artifact,
    classify_resolutions,
    exception_subject,
    validate_resolution,
    validate_subject_action_contract,
)


class ExceptionContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dependencies = [{"evidenceId": "target:zr1:PDB", "semanticFingerprint": "1" * 64}]
        sid = subject_id("zr1", "missing_price_scope", ["PDB"])
        self.subject = exception_subject(
            subject_id_value=sid,
            subject_version_value=subject_version(sid, self.dependencies),
            model="zr1",
            family="price_rules",
            severity="blocking",
            reason_code="missing_price_scope",
            allowed_actions=["provide_typed_value"],
            evidence_dependencies=self.dependencies,
            evidence_references=["Price Schedule!E12"],
            proposed_rows=[],
            gate_impact=["compileReady"],
            question="Provide the exact target scope.",
        )

    def test_resolution_requires_typed_payload_for_kind(self) -> None:
        resolution = {
            "subjectId": self.subject["subjectId"],
            "subjectVersion": self.subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {"bodyStyleScope": "coupe", "trimLevelScope": "1lz"},
            "disposition": "resolved",
            "reviewer": "Sean",
            "reviewedAt": "2026-07-12T00:00:00Z",
        }
        validate_resolution(resolution, self.subject)
        bad = dict(resolution, payload="raw json")
        with self.assertRaisesRegex(ValueError, "typed object"):
            validate_resolution(bad, self.subject)
        garbage = dict(resolution, payload={"garbage": [1, 2, 3]})
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            validate_resolution(garbage, self.subject)

    def test_current_identity_and_relationship_reasons_have_exact_action_contracts(self) -> None:
        contracts = {
            "ambiguous_existing_identity": ("retain_existing",),
            "unresolved_relationship_endpoint": ("choose_relationship", "mark_not_applicable"),
            "unresolved_relationship_identity": ("choose_relationship", "mark_not_applicable"),
            "unsupported_relationship_type": ("choose_relationship", "mark_not_applicable"),
            "unsupported_relationship_direction": ("choose_relationship", "mark_not_applicable"),
        }
        for reason, actions in contracts.items():
            with self.subTest(reason=reason):
                subject = dict(self.subject, reasonCode=reason, allowedActions=list(actions))
                validate_subject_action_contract(reason, actions)

    def test_comparator_proposal_payloads_require_target_owned_values(self) -> None:
        group_subject = dict(
            self.subject,
            reasonCode="comparator_only_rule_group_proposal",
            allowedActions=["provide_typed_value", "mark_not_applicable"],
        )
        validate_resolution(
            {
                "subjectId": group_subject["subjectId"],
                "subjectVersion": group_subject["subjectVersion"],
                "action": "provide_typed_value",
                "payload": {"decision": "confirm_proposal"},
                "disposition": "resolved",
            },
            group_subject,
        )

        exclusive_subject = dict(
            self.subject,
            reasonCode="comparator_only_exclusive_group_proposal",
            allowedActions=["provide_typed_value", "mark_not_applicable"],
        )
        with self.assertRaisesRegex(ValueError, "selectionMode"):
            validate_resolution(
                {
                    "subjectId": exclusive_subject["subjectId"],
                    "subjectVersion": exclusive_subject["subjectVersion"],
                    "action": "provide_typed_value",
                    "payload": {"decision": "confirm_proposal"},
                    "disposition": "resolved",
                },
                exclusive_subject,
            )
        validate_resolution(
            {
                "subjectId": exclusive_subject["subjectId"],
                "subjectVersion": exclusive_subject["subjectVersion"],
                "action": "provide_typed_value",
                "payload": {
                    "decision": "confirm_proposal",
                    "selectionMode": "single_within_group",
                },
                "disposition": "resolved",
            },
            exclusive_subject,
        )

        price_subject = dict(
            self.subject,
            reasonCode="comparator_only_price_rule_proposal",
            allowedActions=["provide_typed_value", "mark_not_applicable"],
        )
        with self.assertRaisesRegex(ValueError, "priceValue"):
            validate_resolution(
                {
                    "subjectId": price_subject["subjectId"],
                    "subjectVersion": price_subject["subjectVersion"],
                    "action": "provide_typed_value",
                    "payload": {"decision": "confirm_proposal"},
                    "disposition": "resolved",
                },
                price_subject,
            )
        validate_resolution(
            {
                "subjectId": price_subject["subjectId"],
                "subjectVersion": price_subject["subjectVersion"],
                "action": "provide_typed_value",
                "payload": {
                    "decision": "confirm_proposal",
                    "priceValue": 995,
                    "bodyStyleScope": "*",
                    "trimLevelScope": "*",
                    "variantScope": "*",
                },
                "disposition": "resolved",
            },
            price_subject,
        )

        default_subject = dict(
            self.subject,
            reasonCode="comparator_only_default_selection_proposal",
            allowedActions=["provide_typed_value", "mark_not_applicable"],
        )
        with self.assertRaisesRegex(ValueError, "priority"):
            validate_resolution(
                {
                    "subjectId": default_subject["subjectId"],
                    "subjectVersion": default_subject["subjectVersion"],
                    "action": "provide_typed_value",
                    "payload": {"decision": "confirm_proposal"},
                    "disposition": "resolved",
                },
                default_subject,
            )
        validate_resolution(
            {
                "subjectId": default_subject["subjectId"],
                "subjectVersion": default_subject["subjectVersion"],
                "action": "provide_typed_value",
                "payload": {
                    "decision": "confirm_proposal",
                    "priority": 10,
                    "displayBehavior": "default_selected",
                },
                "disposition": "resolved",
            },
            default_subject,
        )

    def test_generic_approve_and_skip_are_rejected(self) -> None:
        for action in ("approve", "skip"):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "not allowed"):
                validate_resolution(
                    {"subjectId": self.subject["subjectId"], "subjectVersion": self.subject["subjectVersion"], "action": action, "payload": {}, "disposition": "resolved"},
                    self.subject,
                )

    def test_option_copy_behavior_and_mandatory_charge_payloads_are_strict(self) -> None:
        cases = [
            (
                "copy_review_required",
                "provide_option_copy",
                {"optionName": "Carbon Fiber Wheels", "description": "Visible weave"},
            ),
            (
                "option_behavior_conflict",
                "provide_option_behavior",
                {"active": True, "selectable": False},
            ),
            (
                "mandatory_charge_candidate",
                "confirm_mandatory_charge",
                {"priceValue": 995},
            ),
        ]
        for reason, action, payload in cases:
            with self.subTest(reason=reason):
                subject = dict(self.subject, reasonCode=reason, allowedActions=[action])
                validate_resolution(
                    {
                        "subjectId": subject["subjectId"],
                        "subjectVersion": subject["subjectVersion"],
                        "action": action,
                        "payload": payload,
                        "disposition": "resolved",
                    },
                    subject,
                )
                with self.assertRaises(ValueError):
                    validate_resolution(
                        {
                            "subjectId": subject["subjectId"],
                            "subjectVersion": subject["subjectVersion"],
                            "action": action,
                            "payload": {**payload, "unexpected": True},
                            "disposition": "resolved",
                        },
                        subject,
                    )

    def test_action_disposition_pairs_fail_closed(self) -> None:
        section_subject = dict(
            self.subject,
            reasonCode="missing_section",
            allowedActions=["choose_section"],
        )
        resolution = {
            "subjectId": section_subject["subjectId"],
            "subjectVersion": section_subject["subjectVersion"],
            "action": "choose_section",
            "payload": {"sectionId": "sec_whee_001"},
            "disposition": "retained_existing",
        }
        with self.assertRaisesRegex(ValueError, "requires disposition 'resolved'"):
            validate_resolution(resolution, section_subject)

    def test_unrecognized_typed_value_and_conflicting_current_resolutions_are_rejected(self) -> None:
        unknown_subject = dict(self.subject, reasonCode="unknown_reason")
        resolution = {
            "subjectId": unknown_subject["subjectId"],
            "subjectVersion": unknown_subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {"arbitrary": {"nested": True}},
            "disposition": "resolved",
        }
        with self.assertRaisesRegex(ValueError, "no typed contract"):
            validate_resolution(resolution, unknown_subject)
        malformed_section = dict(
            self.subject,
            reasonCode="unknown_reason",
            allowedActions=["choose_section"],
        )
        with self.assertRaisesRegex(ValueError, "no typed contract"):
            validate_resolution(
                {
                    "subjectId": malformed_section["subjectId"],
                    "subjectVersion": malformed_section["subjectVersion"],
                    "action": "choose_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "disposition": "resolved",
                },
                malformed_section,
            )
        first = {
            "subjectId": self.subject["subjectId"],
            "subjectVersion": self.subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {"bodyStyleScope": "coupe"},
            "disposition": "resolved",
        }
        second = {**first, "payload": {"bodyStyleScope": "convertible"}}
        with self.assertRaisesRegex(ValueError, "Conflicting current resolutions"):
            classify_resolutions([first, second], [self.subject])

    def test_only_media_missing_is_a_nonblocking_deferral(self) -> None:
        self.assertEqual(ALLOWED_DEFERRAL_KINDS, {"asset_map_media_missing"})
        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            build_resolution_artifact("q" * 64, [], deferrals=[{"kind": "missing_price", "disposition": "allowed_deferral"}])

    def test_unrelated_queue_change_keeps_matching_resolution_valid(self) -> None:
        resolution = {
            "subjectId": self.subject["subjectId"],
            "subjectVersion": self.subject["subjectVersion"],
            "action": "provide_typed_value",
            "payload": {"bodyStyleScope": "coupe"},
            "disposition": "resolved",
        }
        first = classify_resolutions([resolution], [self.subject])
        unrelated = exception_subject(
            subject_id_value=subject_id("zr1x", "missing_section", ["BV4"]),
            subject_version_value="v2",
            model="zr1x",
            family="options",
            severity="blocking",
            reason_code="missing_section",
            allowed_actions=["choose_section"],
            evidence_dependencies=[],
            evidence_references=["Equipment Groups 4!A8"],
            proposed_rows=[],
            gate_impact=["compileReady"],
            question="Choose section.",
        )
        second = classify_resolutions([resolution], [self.subject, unrelated])
        self.assertEqual(first["valid"], second["valid"])
        self.assertEqual(second["stale"], [])

    def test_stale_version_is_excluded_from_resolution_semantic_hash(self) -> None:
        stale = {
            "subjectId": self.subject["subjectId"],
            "subjectVersion": "old",
            "action": "provide_typed_value",
            "payload": {"bodyStyleScope": "coupe"},
            "disposition": "resolved",
        }
        classified = classify_resolutions([stale], [self.subject])
        artifact = build_resolution_artifact("q" * 64, classified["valid"], stale_entries=classified["stale"])
        self.assertEqual(artifact["schemaVersion"], "exception-resolutions-1")
        self.assertEqual(artifact["validEntries"], [])
        self.assertEqual(len(artifact["staleEntries"]), 1)

    def test_audit_event_identity_ignores_timestamp_and_reviewer(self) -> None:
        base = build_audit_event(
            queue_subject_fingerprint="q" * 64,
            subject_id_value=self.subject["subjectId"],
            subject_version_value=self.subject["subjectVersion"],
            event_type="stale",
            prior_state="resolved",
            next_state="stale",
            cause_fingerprint="c" * 64,
            reviewer="one",
            occurred_at="one",
        )
        changed = build_audit_event(
            queue_subject_fingerprint="q" * 64,
            subject_id_value=self.subject["subjectId"],
            subject_version_value=self.subject["subjectVersion"],
            event_type="stale",
            prior_state="resolved",
            next_state="stale",
            cause_fingerprint="c" * 64,
            reviewer="two",
            occurred_at="two",
        )
        self.assertEqual(base["eventId"], changed["eventId"])


if __name__ == "__main__":
    unittest.main()
