"""Images workspace parity with the other five recovered workspaces.

Owned by `docs/superpowers/specs/2026-08-27-images-workspace-parity.md`.

The 2026-08-21 UX recovery rebuilt five of six workspaces and gave Images one
clause — "the existing asset reconciliation capability in user-facing language"
— so `AssetManager.jsx` missed Checkpoint 3C (shared editor shell), 3F
(navigation state) and 6 (operator lifecycle language). Each test below closes
one of those three gaps and states the change that makes it fail again.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "workbook-manager" / "frontend" / "src"
ASSET_SCOPE = SRC / "assetScope.js"


def _read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def _run_asset_scope(script: str):
    result = subprocess.run(
        [
            "node", "--input-type=module", "--eval",
            f"import * as scope from {json.dumps(ASSET_SCOPE.as_uri())};" + script,
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class TestImagesWorkspaceParity(unittest.TestCase):
    def setUp(self) -> None:
        self.asset_manager = _read("components", "AssetManager.jsx")
        self.app = _read("App.jsx")
        self.navigation = _read("navigationState.js")

    def test_image_decision_opens_in_the_shared_editor_shell(self):
        """§3C. Fails again if the inspector returns to an inline panel.

        The shell owns focus trap, Escape, dirty-close confirmation, body scroll
        lock and focus restore; an inline `panel` has none of them.
        """
        self.assertIn('import EditorShell from "./EditorShell.jsx";', self.asset_manager)
        # Anchored on the line break so a renamed element (`<EditorShellX`) cannot
        # satisfy this as a substring — the element must be exactly the shell.
        self.assertIn("    <EditorShell\n", self.asset_manager)
        self.assertIn("    </EditorShell>\n", self.asset_manager)
        # The shell can only refuse a silent close if it is given a real dirty
        # signal, so the prop must be wired to computed state, not a literal.
        self.assertIn("dirty={dirty}", self.asset_manager)
        self.assertIn("onRequestClose={onClose}", self.asset_manager)
        self.assertNotIn('className="asset-inspector panel"', self.asset_manager)

    def test_dirty_signal_covers_preview_and_resolution_selections(self):
        """§3C. Fails again if any pending resolution choice is unguarded.

        `preview` is seeded from `initial`, while candidate, inventory, and
        assignment choices have independent state and can remain meaningful
        even when the resulting URL equals the seeded preview.
        """
        self.assertIn("const dirty = useMemo(", self.asset_manager)
        self.assertIn(
            "JSON.stringify(preview) !== JSON.stringify(initial)", self.asset_manager
        )
        self.assertIn(
            "Boolean(selectedCandidate || inventoryUrl || targetItemId)",
            self.asset_manager,
        )
        self.assertIn(
            "[preview, initial, selectedCandidate, inventoryUrl, targetItemId]",
            self.asset_manager,
        )

    def test_open_image_decision_is_navigation_state(self):
        """§3F. Fails again if selection returns to component state.

        Component state cannot be linked, does not survive reload, and is lost
        when a draft starts.
        """
        self.assertIn('"asset"', self.navigation)
        self.assertIn(
            'const selectedId = navigation?.type === "asset" ? navigation.id || "" : "";',
            self.asset_manager,
        )
        self.assertIn("const selectAsset = useCallback(", self.asset_manager)
        self.assertIn("onClick={() => selectAsset(item.id)}", self.asset_manager)
        self.assertNotIn("setSelectedId", self.asset_manager)

    def test_asset_is_a_routable_entity_type(self):
        """§3F. Fails again if `asset` is dropped from the entity allowlist.

        `parseNavigation` and `serializeNavigation` both gate on ENTITY_TYPES, so
        an absent member silently discards the id in both directions.
        """
        entity_line = next(
            line for line in self.navigation.splitlines() if '"exclusive_group"' in line
        )
        self.assertIn('"asset"', entity_line)

    def test_app_passes_navigation_to_the_images_workspace(self):
        """§3F. Fails again if the workspace goes back to `setModelKey` alone."""
        block = self.app.split("<AssetManager", 1)[1].split("/>", 1)[0]
        self.assertIn("navigation={navigation}", block)
        self.assertIn("onNavigationChange={commitNavigation}", block)

    def test_workspace_names_draft_state_in_operator_lifecycle_language(self):
        """§6/§14.4. Fails again if this workspace phrases draft state itself.

        The tray and Review & Apply both render `operatorLifecycle`; a third
        wording for the same state is the defect.
        """
        self.assertIn(
            'import { operatorLifecycle } from "./ChangesSync.jsx";', self.asset_manager
        )
        self.assertIn(
            "operatorLifecycle[draftLifecycle?.draft?.status]", self.asset_manager
        )

    def test_a_linked_decision_is_resolved_outside_the_current_page_and_filters(self):
        """§3F. Fails again if reload only checks the visible queue page.

        The locator deliberately omits UI filters and walks bounded server pages,
        so a link created under another filter or page still opens after reload.
        """
        locator = self.asset_manager.split("async function findLinkedAsset", 1)[1].split(
            "export default function AssetManager", 1
        )[0]
        self.assertIn("limit: LINK_LOOKUP_PAGE_SIZE", locator)
        self.assertIn("draft_id: draftId", locator)
        self.assertNotIn("...filters", locator)
        self.assertIn("candidate.id === itemId", locator)
        self.assertIn("offset >= result.queue.total", locator)
        self.assertIn("findLinkedAsset(selectedId, draftId)", self.asset_manager)
        self.assertIn("linkedAsset.id === selectedId ? linkedAsset.item : null", self.asset_manager)

    def test_opening_the_workspace_does_not_auto_open_a_decision(self):
        """§3C. Fails again if load() re-selects the first queue item.

        Under the shell that would open a modal dialog over the workspace on
        every load, before the operator has chosen anything.
        """
        self.assertNotIn("result.queue.items[0]?.id", self.asset_manager)

    def test_images_scope_adapter_distinguishes_one_model_from_explicit_all_models(self):
        """IMG-SCOPE-01/02: one owner drives queries, decisions, and target choices."""
        result = _run_asset_scope(
            "const rows=[{model_key:'stingray'},{model_key:'z06'},{model_key:''}];"
            "console.log(JSON.stringify({"
            "oneQuery:scope.reconciliationModel('stingray'),"
            "allQuery:scope.reconciliationModel(scope.ALL_MODELS),"
            "oneMatches:rows.map(row=>scope.assetInScope(row,'stingray')) ,"
            "allMatches:rows.map(row=>scope.assetInScope(row,scope.ALL_MODELS)),"
            "oneTargets:scope.assignmentTargetsInScope(rows,'z06')"
            "}));"
        )
        self.assertEqual(result["oneQuery"], "stingray")
        self.assertEqual(result["allQuery"], "")
        self.assertEqual(result["oneMatches"], [True, False, False])
        self.assertEqual(result["allMatches"], [True, True, True])
        self.assertEqual(result["oneTargets"], [{"model_key": "z06"}])

    def test_global_header_owns_the_images_all_models_scope(self):
        """IMG-SCOPE-01: Images cannot retain a second model selector."""
        self.assertIn('tab === "assets" && <option value="*">All models</option>', self.app)
        self.assertIn('navigation.model === "*" && workspace !== "assets"', self.app)
        filter_bar = self.asset_manager.split('className="panel-head asset-filter-bar"', 1)[1]
        self.assertNotIn("filters.model", self.asset_manager)
        self.assertNotIn('<option value="">All models</option>', filter_bar)
        self.assertIn("model: reconciliationModel(modelKey)", self.asset_manager)

    def test_clear_filters_preserves_the_global_model_scope(self):
        """IMG-SCOPE-01: clear resets only secondary Images filters."""
        clear_handler = self.asset_manager.split(">Clear filters</button>", 1)[0].rsplit(
            'onClick={() => {', 1
        )[1]
        self.assertIn("setFilters(EMPTY_FILTERS)", clear_handler)
        self.assertNotIn("model", clear_handler)
        self.assertNotIn("setModelKey", clear_handler)

    def test_only_the_latest_model_request_can_replace_visible_images(self):
        """IMG-SCOPE-03: a slow prior model response cannot overwrite current scope."""
        self.assertIn("const requestRef = React.useRef(0);", self.asset_manager)
        self.assertIn("const requestId = ++requestRef.current;", self.asset_manager)
        self.assertIn("if (requestId !== requestRef.current) return;", self.asset_manager)
        self.assertIn("dataScope === modelKey ? data : null", self.asset_manager)

    def test_out_of_scope_deep_link_is_refused_until_scope_changes_explicitly(self):
        """IMG-SCOPE-02: links never switch models or expose cross-scope actions."""
        self.assertIn("const selectedInScope = assetInScope(selected, modelKey);", self.asset_manager)
        self.assertIn("This image decision belongs to", self.asset_manager)
        self.assertIn("Switch the visible scope", self.asset_manager)
        self.assertIn("onClick={() => setModelKey(selected.model_key || ALL_MODELS)}", self.asset_manager)
        self.assertIn("{selected && selectedInScope && (", self.asset_manager)

    def test_assignment_targets_follow_the_same_visible_scope(self):
        """IMG-SCOPE-02: a scoped decision cannot target another model."""
        self.assertIn(
            "assignmentTargetsInScope(data.assignment_targets || [], modelKey)",
            self.asset_manager,
        )

    def test_bulk_safe_acceptance_sends_the_visible_model_scope(self):
        """IMG-SCOPE-02: bulk acceptance stages only the visible scope's items.

        The toolbar's safe-proposal count is the server-scoped count; the bulk
        payload must carry the same effective model so acceptance cannot
        diverge from what the operator sees when several models have proposals.
        """
        toolbar = self.asset_manager.split('"asset-draft-toolbar', 1)[1]
        self.assertIn("boundPayload({ model: reconciliationModel(modelKey) })", toolbar)


if __name__ == "__main__":
    unittest.main()
