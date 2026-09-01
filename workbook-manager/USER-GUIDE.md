# Workbook Manager User Guide

The Workbook Manager opens in a web browser, but it runs only on your Mac. It
is not a public website.

Use it to review and prepare changes to `stingray_master.xlsx`, including model
information, options, prices, rules, and images.

> **The most important rule:** Saving a change only adds it to a draft. It does
> not change the workbook. The workbook changes only when you finish the full
> **Apply and Rebuild** process.

## The short version

```text
Make changes → Save them to the draft → Review everything → Freeze the draft
→ Run Workbook Preview → Approve Exact Preview → Apply and Rebuild → Re-Import Workbook
```

Do not skip the review steps. They are there to catch mistakes before the
workbook changes.

## 1. Open the Manager

1. Close `stingray_master.xlsx` in Excel.
2. Open Terminal.
3. Paste these two lines, one at a time:

   ```sh
   cd /Users/seandm/Projects/27vette
   ./workbook-manager/run.sh
   ```

   You do not need to understand these commands. Copy them exactly as shown.

4. Leave the Terminal window open.
5. Open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser.
6. Wait for the model names to appear. The first opening may take a little
   longer while the Manager reads the workbook.

To stop the Manager, return to Terminal and press `Control-C`.

Only run one copy of the Manager at a time.

If you close and reopen the Manager, it will try to return you to the newest
unfinished draft. Always review the draft number and its pending changes before
continuing.

## 2. Check the top status bar

The top of the page shows five small status labels. These are the plain-English
meanings:

| On-screen label | What it means |
| --- | --- |
| `projection` | The Manager's working view of the workbook. `current` means it is ready to use. |
| `draft` | The state of the changes you are preparing. |
| `workbook` | Whether the real Excel workbook is ready and unchanged since it was last checked. |
| `generated artifacts` | Whether the local model files match the last completed change. |
| `publication` | Whether the local order-form data matches the last completed change. |

If you see `loading`, wait a moment. If you see an error, an Excel lock, or a
message saying the workbook changed on disk, follow [If something goes
wrong](#if-something-goes-wrong) before editing.

## 3. Choose where to work

The Manager has seven workspaces:

| Tab | Use it for |
| --- | --- |
| **Form Overview** | Model and form copy, steps/sections, plus registered promotion, source-routing, variant, and order-summary structure. |
| **Sections & Layout** | Section structure and layout details. |
| **Options & Relationships** | Options, prices, rules, colors, interiors, and connected model details. |
| **Groups** | Rule and exclusive-group relationships. |
| **Images** | Image coverage, missing or broken images, matching, crop, and position. |
| **Review & Apply** | Review every pending change and complete the final approval process. |
| **Advanced & Recovery** | Durable workflow history, recovery evidence, and the raw collection browser. |

## 4. Make a normal workbook change

### Change model or form information

1. Open **Form Overview**.
2. Choose the model.
3. Use **Edit model metadata & Vehicle Setup copy** to change the model name or
   setup wording.
4. Use a pencil button to edit a step or section.
5. Use **Add Section Presentation** only when a new section display entry is
   truly needed.
6. Select **Save Update to Draft** or **Save Add to Draft**.

### Change registered workbook structure

1. Open **Form Overview** and find **Registered structure management**.
2. Choose promotion, workbook source routing, variant definitions, model variant
   membership, order-summary sections, or step-to-summary mappings.
3. Confirm the model/shared scope, source sheet, and generated-impact note.
4. Select **Add** or a row's pencil button. Review the lineage, dependency,
   active-state, and impact evidence before saving.
5. Save the change to the durable draft. This does not write the workbook or
   rebuild generated files.

Read-only registered families explain why their controls are blocked. Delete
requests still use the registered dependency check and must be completed as an
explicit graph in the draft; the Manager does not choose promotion, routing,
membership, labels, or ordering for you.

### Change an option, price, rule, color, or other model item

1. Open **Options & Relationships**.
2. Choose the model across the top.
3. Choose the type of information on the second row.
4. Use **Search all fields** to find the item.
5. Select the pencil button to edit it, or **Add** to create a new item.
6. Make the change.
7. Select **Save Update to Draft** or **Save Add to Draft**.

The screen will confirm that the change was saved to the draft. The workbook
has not changed yet.

If a group is marked **read-only**, it cannot be changed from this Manager. Do
not try to work around that restriction.

### Delete something

1. Select the trash button beside the item.
2. If the Manager lists related items, read the list carefully.
3. Add every required related deletion to the same draft before final review.
4. Do not continue to final approval while the Manager says a required related
   item is missing.

## 5. Review and fix images

Open **Images**, then select **Refresh inventory** when you want the
latest image list.

The coverage cards show how much of each model or section already has images.
Select a card or one of the status boxes to narrow the list.

### What the image status names mean

| Status | What it means | What to do |
| --- | --- | --- |
| **Safe proposals** | The Manager found one clear match. | Inspect it, then use **Add safe proposal to draft**. Use **Add all safe matches to draft** only when you are comfortable accepting the whole clear-match group. |
| **Covered** | The workbook already has an image for this item. | Leave it alone, or adjust its display using **Save presentation edits to draft**. |
| **Missing** | An image is expected, but none is assigned. | Search the available image list and choose **Use selected inventory image**. Use a manual link only when you have checked it carefully. |
| **Ambiguous** | More than one image could match. | Compare the choices, select the correct one, then choose **Use explicitly selected candidate**. |
| **Unmatched media** | An available image is not connected to a workbook item. | Assign it to the correct target, or ignore it only when it truly does not belong. |
| **Unparseable media** | The Manager cannot tell what an available image belongs to. | Assign it manually when you know the answer, or ignore that exact image. |
| **Dead URLs** | A saved image link no longer loads. | Replace it when the Manager offers a clear action. If no action is offered, leave it unresolved and record the item for follow-up. |
| **Stale targets** | An old image row points to something that is no longer current. | Review it, then use **Add explicit stale-row deactivation** when it should be turned off. |
| **Wildcard conflicts** | A broad image assignment clashes with a more specific one. | Treat **Edit presentation only** and **Resolve ownership conflict** as separate decisions. Create exact model ownership when that is the intended owner. Update shared wildcard ownership only when the Manager says every affected model has one unambiguous candidate; otherwise leave the blocked conflict unresolved. |
| **Ignored media** | That exact image was intentionally skipped earlier. | No action is needed unless the image list changes and it returns for review. |

Image and assignment-target searches return one bounded page at a time. Target
results lead with the workbook-authored name and retain the canonical ID, model,
type, and section underneath. **No matches** means the search succeeded with no
result. A red failure message means the search did not complete; use **Retry**
instead of treating it as an empty inventory. If the inventory or target
fingerprint changes, search again before saving. Refreshing reconciliation keeps
the open item and unsaved candidate/target choice so you can finish or close it
explicitly.

### Adjust how an image looks

Select an item in the **Resolution inbox**. The Manager shows the current image
beside the selected replacement.

- **Fit — cover:** fills the space and may crop the edges.
- **Fit — contain:** shows the whole image and may leave empty space.
- **Fit — swatch:** displays a wide color strip.
- **Position picker:** moves the important part of the image left, right, up,
  down, or center.
- **Hover image:** controls the second image shown for supported body-style
  cards.
- **Image alt text:** briefly describes the image for people who cannot see it.

The card preview is a helpful guide, not proof of the finished order form. The
final local model files are rebuilt only after **Apply and Rebuild** succeeds.

The Images workspace does not upload, delete, or rename WordPress images. A manual
image link must already exist and load correctly.

## 6. Review the complete draft

Open **Review & Apply**. The number beside the workspace is the number of pending
workbook changes.

1. Read every item in **Draft operations**.
2. Check the model, item name, and before-and-after values.
3. Review image decisions shown with those changes.
4. If one operation is wrong and the draft is still open, select **Discard
   operation** on that item. Read the confirmation, including how many changes
   and affected models remain, before confirming. You can also return to the
   earlier workspace and save the authored value again; a full reversion
   removes that effective operation.
5. When everything is correct, select **Freeze ChangeSet**.

“Freeze ChangeSet” means “lock this exact group of changes.” After you freeze
it, you cannot edit that draft. If you discover a mistake afterward, select
**Cancel Draft** and start a new draft.

## 7. Preview, approve, and apply

After freezing the draft, the Manager reveals the next button one step at a
time.

1. Select **Run Workbook Preview**.
2. Read **Warnings & failures**.
3. If the preview is rejected, do not force it. Select only the operations you
   want to keep, enter your name and a concrete correction reason, then select
   **Create correction draft**. The rejected ChangeSet and failed validation
   stay in history; the Manager opens the new mutable draft with the retained
   operations so you can correct only what failed without recreating unrelated
   valid work.
4. If the preview is ready, enter your name in **Operator**.
5. If warnings are shown, accept only the warnings you understand and intend to
   allow.
6. Select **Approve Exact Preview**.
7. Make sure Excel is closed and the top of the page does not show **Excel lock
   present**.
8. In the confirmation box, type exactly:

   ```text
   APPLY AND REBUILD
   ```

9. Select **Apply and Rebuild**.
10. Keep the browser and Terminal open until the result appears.

This final action changes the workbook and rebuilds only the affected local
model files. It also keeps safety copies so it can restore the prior files if a
later step fails and the Manager can confirm that the restore worked.

## 8. Check the result

A successful result normally shows:

| Result box | Expected result |
| --- | --- |
| **Workbook** | `applied` |
| **Projection** | `stale` — this is expected because the Manager is still showing its pre-change working view. |
| **Generated contracts** | `current` |
| **Publication** | `current` |

Then:

1. Select **Re-Import Workbook** under **Projection tools**.
2. Wait for the import message to say it completed with no issues.
3. Select **Start New Draft** when you are ready for another group of changes.

**Apply and Rebuild does not publish a website, clear the live website cache,
change WordPress media, or send anything to a dealer.** Those are separate
jobs.

## 9. Review workflow history

Open **Advanced & Recovery** to review completed, cancelled, rejected, restored,
or recovery-required workflow outcomes. **Workflow history** is the current
durable record. Filter it by affected model or outcome, and use **Open exact
draft** to inspect the bound draft and its immutable attempts. Expand
**Technical evidence** only when exact hashes or attempt details are needed.

**Legacy staging history** is a separate read-only disclosure for the retired
staging/sync workflow. Its rows are not included in Workflow history totals.
Workflow history remains available when the Manager cannot verify or load the
disposable workbook projection, so recovery evidence can still be inspected.

## If something goes wrong

### The page does not open

- Make sure the Terminal window is still open and the start command is still
  running.
- Make sure only one copy of the Manager is running.
- Copy the Terminal message before closing anything; it usually explains what
  stopped.
- If the message says something is missing, stop and keep the message. Do not
  install or replace anything by guessing.

### The Manager says “Excel lock present”

Close the workbook in Excel, wait a few seconds, then select **Refresh** in
**Review & Apply**.

### The Manager says “workbook changed on disk”

If you do not have an unfinished draft, select **Re-Import Workbook**. If you do
have an unfinished draft, stop and review why the workbook changed before doing
anything else.

### The Manager shows blocking findings

Do not continue, delete records, or try to bypass the message. Copy the full
message and fix the listed workbook problem first.

### A preview or Apply and Rebuild fails

Read **Apply failure summary** first. It names the failed stage, error, workbook
and output rollback state, whether retry or cancellation is safe, and the next
available action. Then read **Warnings & failures**; expand the latest immutable
attempt only when you need the raw technical evidence. Use **Retry** only when
the summary says it is safe and you understand what was fixed. If **Cancel
Draft** is offered and you want to abandon the change, use it.

### The Manager says “Manual recovery required”

Stop. Do not guess and do not select a manual result just to clear the message.
The workbook and rebuilt files must be checked independently before any manual
choice is recorded.

## Other buttons in Review & Apply

- **Re-Import Workbook:** refreshes the Manager's working view from the real
  workbook.
- **Export Disposable Comparison:** creates a review copy. Never use it to
  replace `stingray_master.xlsx`.
- **Backup Manager State:** saves the Manager's drafts and history. It is not a
  replacement for the workbook's own safety copy.
- **Refresh:** reloads the latest status and draft information.
- **Cancel Draft:** closes the unfinished draft without applying it to the
  workbook.
