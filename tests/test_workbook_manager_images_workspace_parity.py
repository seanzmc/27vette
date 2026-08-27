"""Images workspace parity with the other five recovered workspaces.

Owned by `docs/superpowers/specs/2026-08-27-images-workspace-parity.md`.

The 2026-08-21 UX recovery rebuilt five of six workspaces and gave Images one
clause — "the existing asset reconciliation capability in user-facing language"
— so `AssetManager.jsx` missed Checkpoint 3C (shared editor shell), 3F
(navigation state) and 6 (operator lifecycle language). Each test below closes
one of those three gaps and states the change that makes it fail again.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "workbook-manager" / "frontend" / "src"


def _read(*parts: str) -> str:
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


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

    def test_dirty_signal_compares_preview_against_its_seed(self):
        """§3C. Fails again if `dirty` is hardcoded or dropped.

        `preview` is seeded and re-seeded from `initial`, so that is the only
        comparison that reports real unsaved operator edits.
        """
        self.assertIn("const dirty = useMemo(", self.asset_manager)
        self.assertIn(
            "JSON.stringify(preview) !== JSON.stringify(initial)", self.asset_manager
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

    def test_a_linked_decision_outside_the_current_page_is_reported(self):
        """§3F. Fails again if an unresolvable link renders as an empty page.

        The queue is filtered and paginated, so a valid link can point outside
        the loaded page; silence there is indistinguishable from a broken link.
        """
        self.assertIn("{selectedId && !selected && (", self.asset_manager)
        self.assertIn("The linked image decision is not in the current filter", self.asset_manager)

    def test_opening_the_workspace_does_not_auto_open_a_decision(self):
        """§3C. Fails again if load() re-selects the first queue item.

        Under the shell that would open a modal dialog over the workspace on
        every load, before the operator has chosen anything.
        """
        self.assertNotIn("result.queue.items[0]?.id", self.asset_manager)


if __name__ == "__main__":
    unittest.main()
