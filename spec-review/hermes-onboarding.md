# Hermes Agent Onboarding for 27vette

Here is the amended version using the actual Nous Research Hermes Agent docs.

---

## Correction to the Earlier Framing

My earlier answer treated "Hermes" as a generic orchestration layer. The official docs describe Hermes Agent as more than that: a self-improving autonomous agent with persistent memory, skills, terminal/file tools, web/browser tools, messaging gateways, MCP integrations, profiles, worktrees, checkpoints, and editor integration. The main adjustment is this:

|                        | Framing                                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Earlier framing**    | Hermes = coordinator over Codex                                                                                                                                                             |
| **Better framing**     | Hermes = persistent local/remote agent environment; Codex = coding-specialized implementation/review tool                                                                                   |
| **Best 27vette setup** | Hermes manages context, workflows, skills, recurring audits, mobile access, and repo orchestration; Codex handles high-signal implementation/review passes when you deliberately invoke it. |

Hermes' docs explicitly position it as an agent that "creates skills from experience," improves skills during use, persists knowledge, and can run on a laptop, VPS, serverless sandbox, or messaging platform rather than being tied to an IDE.

---

## Why Hermes Fits Your 27vette Project

The current 27vette main branch is a live static Corvette order-form app for Stingray and Grand Sport. The repo says the static browser app lives in `form-app/index.html`, `form-app/styles.css`, `form-app/app.js`, and generated `form-app/data.js`; dealer submissions post through the WordPress endpoint with Cloudflare Turnstile.

The source-of-truth direction is workbook-first:

```
stingray_master.xlsx
  -> workbook source sheets
  -> generator / inspection scripts
  -> generated form_* workbook sheets
  -> form-output/*.json and *.csv
  -> form-app/data.js
  -> static browser runtime
  -> download build / submit to dealer
```

The repo explicitly says business rules belong in workbook data, scripts should stay procedural/general, and the runtime should render/evaluate generated data rather than accumulating hardcoded Corvette ordering logic.

Hermes is useful here because your project's biggest risk is not "can an AI write code?" It is: **can an AI remember the rules, avoid drifting, split work into narrow passes, run the right gates, and not hardcode RPO logic in the wrong layer?**

---

## Best Hermes Use Cases for 27vette

### 1. Persistent Project Memory

Hermes has bounded persistent memory stored under `~/.hermes/memories/`, split into `MEMORY.md` for environment/workflow facts and `USER.md` for user preferences. The docs say memory is injected into the system prompt at session start and is meant for things like project conventions, environment facts, tool quirks, workflow habits, and completed-task lessons.

For you, Hermes should remember:

- 27vette lives on main as a live customer-facing Stingray + Grand Sport app.
- `stingray_master.xlsx` is canonical business data.
- Do not edit generated `form_*` sheets directly.
- Do not expand hardcoded RPO/model-specific Python or JS behavior.
- Use spec-first workflow.
- Keep passes small.
- Run targeted Node tests and generator checks.
- Sean uses a MacBook Pro M2 Max and prefers precise, stepwise instructions.

This is exactly the kind of persistent operating context that repeatedly gets lost when starting new AI sessions.

### 2. Project Instructions Through AGENTS.md

Hermes automatically discovers project context files. Its docs say `.hermes.md` / `HERMES.md` has highest priority, then `AGENTS.md`, then `CLAUDE.md`, then Cursor rules; `AGENTS.md` is described as the primary project context file for structure, conventions, and special instructions.

Your repo already has a strong `AGENTS.md`, so Hermes should use that rather than inventing a separate rule system. That file already requires spec-first mode for non-trivial work and requires handoffs to report what changed, what did not change, gate results, pending manual verification, residual risks, and follow-up work.

### 3. Skills for Repeatable 27vette Workflows

Hermes skills are on-demand knowledge documents stored in `~/.hermes/skills/`. They can be invoked as slash commands and follow a progressive-disclosure pattern so the full instructions only load when needed.

This is a strong fit for your recurring workflows. I would create custom Hermes skills like:

| Skill                     | Purpose                                                                                             |
| ------------------------- | --------------------------------------------------------------------------------------------------- |
| `/27vette-pass-plan`      | Creates a spec-first migration pass with scope, files, risks, validation, and approval question.    |
| `/27vette-gate`           | Runs the correct validation commands based on changed files.                                        |
| `/27vette-workbook-guard` | Checks whether a proposed fix belongs in workbook data, generator logic, runtime JS, or tests.      |
| `/27vette-image-audit`    | Audits RPO image assets, duplicate filenames, missing RPO coverage, and unlinked image files.       |
| `/27vette-codex-prompt`   | Writes a Codex prompt with recommended reasoning level and explicit report-only vs migration scope. |

Hermes can also create or update skills after it discovers a working process; the docs describe agent-managed skills as procedural memory created after complex tasks, corrections, or non-trivial workflows.

### 4. Worktree Isolation for Agent Work

Hermes has first-class git worktree guidance. The docs say worktrees are the safest way to run multiple agents in parallel or isolate experimental refactors, because each agent gets its own branch and working directory. Hermes also has a built-in `-w` flag that creates a temporary worktree under `.worktrees/` with an isolated branch.

For 27vette, this is critical. Do not let Hermes, Codex, and manual edits all operate in the same dirty checkout. Use one worktree per pass:

```bash
cd ~/Projects/27vette
git status
hermes -w
```

Or manual:

```bash
cd ~/Projects/27vette
git worktree add ../27vette-hermes-image-audit feature/hermes-image-audit
cd ../27vette-hermes-image-audit
hermes
```

### 5. Checkpoints and Rollback

Hermes has optional checkpoints. When enabled, it snapshots before file writes, patches, and destructive terminal commands; `/rollback` can list, preview, or restore checkpoints. The checkpoint store is separate from the real project `.git`.

For your project, turn checkpoints on for Hermes coding sessions:

```bash
hermes chat --checkpoints
```

Or globally in config:

```yaml
checkpoints:
  enabled: true
```

This does not replace git commits, but it gives you a fast recovery layer when an agent makes a bad patch between commits.

### 6. Messaging Access From Your Phone

Hermes can run a messaging gateway for Telegram, Discord, Slack, WhatsApp, Signal, SMS, Email, Microsoft Teams, and more. The gateway handles sessions, cron jobs, and voice messages, and it can run as a background service on macOS via launchd.

For your dealership workflow, this is unusually useful. You could message Hermes from your phone while interrupted at work:

```
Run /27vette-pass-plan for Grand Sport image asset mapping.
Do not edit files. Report what workbook fields would be needed.
```

Security matters here because messaging platforms can expose terminal access. Hermes' docs say the gateway denies users by default unless they are allowlisted or paired, and platform-specific allowlists can be configured.

### 7. ACP Editor Integration

Hermes can run as an ACP server so compatible editors can talk to Hermes over stdio and render chat, tool activity, diffs, terminal commands, approval prompts, and streamed responses. The ACP mode exposes editor-focused tools like file read/write/patch/search, terminal/process, web/browser tools, memory, todo, session search, skills, execute_code, delegate_task, and vision.

For your Mac setup, this means Hermes can be used inside VS Code through the ACP Client extension, or in Zed through its ACP registry/custom agent configuration. The docs provide a VS Code manual configuration using:

```json
{
  "acp.agents": {
    "Hermes Agent": {
      "command": "hermes",
      "args": ["acp"]
    }
  }
}
```

This is the cleanest "editor-native Hermes" route. It is separate from Codex, but both can coexist in the same repo.

---

## The Correct Hermes + Codex Relationship

I did not find an official Hermes doc that says Hermes directly "connects to Codex" as a native integration. So I would not describe this as a built-in Hermes-to-Codex bridge.

The practical setup is:

**Hermes:**

- persistent project agent
- remembers your preferences and 27vette workflows
- owns skills, checklists, audits, worktree orchestration, phone access, MCP tools

**Codex:**

- implementation/review coding agent
- reads the same repo `AGENTS.md`
- handles focused code changes, tests, and PR review

Codex CLI can run locally from your terminal, read/change/run code in the selected directory, and is installed with `npm i -g @openai/codex`. Codex also reads `AGENTS.md` files before doing work, layering global guidance with project-specific instructions.

So the best bridge is **shared repo rules + explicit prompts + git branches/PRs**, not hidden background coupling.

---

## Detailed Setup Walkthrough

### Step 1: Install Hermes on Your Mac

Run:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

The Hermes docs list this one-line installer for Linux/macOS/WSL2 and say the installer handles dependencies, the repo clone, virtual environment, global `hermes` command setup, and model/provider configuration.

Then reload your shell:

```bash
source ~/.zshrc
```

Start Hermes:

```bash
hermes
```

Run diagnostics:

```bash
hermes doctor
```

The docs recommend `hermes doctor` for diagnostics when something is missing.

### Step 2: Configure Model/Provider

Run:

```bash
hermes model
```

Use whatever provider you want for Hermes. Since you already use OpenAI/Codex workflows, a reasonable setup is:

- **Hermes:** general orchestration, memory, skills, audits
- **Codex:** repo edits, subagents, GitHub PR review

Hermes stores settings in `~/.hermes/config.yaml` and secrets/API keys in `~/.hermes/.env`; the docs say secrets belong in `.env`, while model, terminal backend, compression, memory, and toolsets belong in `config.yaml`.

### Step 3: Configure Hermes Tools

Run:

```bash
hermes tools
```

For 27vette, enable only the useful surfaces at first:

**Recommended:**

- terminal
- file
- search
- memory
- skills
- todo
- browser/web if you want docs lookup
- delegation only after you trust the setup

**Avoid at first:**

- messaging delivery
- cronjob
- home automation
- broad MCP servers
- anything with unnecessary write powers

Hermes toolsets include terminal/file manipulation, browser automation, memory, session search, cron jobs, code execution, delegation, and MCP integrations.

### Step 4: Create a Dedicated 27vette Hermes Profile

Create a profile:

```bash
hermes profile create vette-coder --clone
```

Then configure it:

```bash
vette-coder setup
```

Set its default working directory:

```bash
vette-coder config set terminal.cwd /Users/seandm/Projects/27vette
```

Adjust the path if your local repo is elsewhere.

Hermes profiles are separate home directories, each with its own config, `.env`, `SOUL.md`, memories, sessions, skills, cron jobs, and state database. Creating a profile also creates a command alias, so `vette-coder chat` targets that profile.

> **Important distinction:** profiles isolate Hermes state, but they do not sandbox filesystem access. The docs explicitly say a profile is not a sandbox; on the local backend, the agent still has the same filesystem access as your user account.

### Step 5: Use Worktree Mode by Default for 27vette

Run:

```bash
cd ~/Projects/27vette
vette-coder -w
```

Hermes will create an isolated worktree under `.worktrees/` with its own branch. This should be your default for any repo-editing session.

For report-only audits where no edits should happen:

```bash
cd ~/Projects/27vette
vette-coder chat -q "Read AGENTS.md and codex-context.md. Report-only. Do not edit files. Summarize the current 27vette architecture and validation gates."
```

### Step 6: Enable Checkpoints

Run:

```bash
vette-coder chat --checkpoints
```

Or add this to `~/.hermes/profiles/vette-coder/config.yaml`:

```yaml
checkpoints:
  enabled: true
  max_snapshots: 20
  max_total_size_mb: 500
  max_file_size_mb: 10
```

Hermes checkpoints are opt-in and are taken before file tools and destructive commands.

### Step 7: Add a 27vette Hermes Skill

Create:

```bash
mkdir -p ~/.hermes/profiles/vette-coder/skills/dev/27vette-pass-plan
nano ~/.hermes/profiles/vette-coder/skills/dev/27vette-pass-plan/SKILL.md
```

Paste:

```markdown
---
name: 27vette-pass-plan
description: Spec-first planning workflow for 27vette development passes.
version: 1.0.0
metadata:
  hermes:
    category: dev
    tags: [27vette, corvette, workbook, codex, planning]
---

# 27vette Pass Plan

## When to Use

Use this skill before any non-trivial 27vette change, especially when touching:

- stingray_master.xlsx
- scripts/generate_stingray_form.py
- scripts/generate_grand_sport_form.py
- scripts/corvette_form_generator/
- form-app/app.js
- form-app/data.js
- form-output/
- tests/

## Procedure

1. Read AGENTS.md and codex-context.md.
2. Determine whether the task is:
   - report-only
   - docs-only
   - workbook/data-only
   - generator-only
   - runtime-only
   - test-only
   - mixed
3. Identify exact files, workbook sheets, generated artifacts, and tests.
4. Check whether the fix belongs in workbook source data, generator logic, runtime logic, or tests.
5. Reject hardcoded model/RPO exceptions unless explicitly approved.
6. Produce a spec before edits.

## Required Output

- Diagnosis
- Proposed scope
- Files/sheets/artifacts affected
- Risks and non-goals
- Validation plan
- Approval question

## Project Rules

- Business rules belong in workbook-authored data when the workbook can represent them.
- Do not edit generated form\_\* sheets directly.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior without explicit approval.
- Keep passes small.
- Evidence beats assumption.
```

Then in Hermes:

```
/27vette-pass-plan Plan the next pass for adding image assets to selectable RPOs. Report-only. Do not edit files.
```

### Step 8: Install Codex CLI

```bash
npm i -g @openai/codex
codex
```

Codex CLI install/run commands are officially documented as `npm i -g @openai/codex` and `codex`; first run prompts sign-in with ChatGPT or an API key.

### Step 9: Keep Codex Aligned With 27vette Rules

Your repo already has `AGENTS.md`, and Codex reads `AGENTS.md` before work. Codex discovery starts with global guidance in `~/.codex`, then project guidance from the repo root down to the current directory.

Create global Codex guidance:

```bash
mkdir -p ~/.codex
nano ~/.codex/AGENTS.md
```

Paste:

```markdown
# Sean's Codex Defaults

- Use spec-first mode for non-trivial work.
- State report-only vs migration/edit scope clearly.
- Keep passes small and reversible.
- Do not add dependencies without approval.
- Do not refactor unrelated code.
- Run the requested validation gates.
- For 27vette, obey the repo AGENTS.md and treat workbook source-of-truth rules as hard constraints.
- When writing Codex prompts for Sean, include recommended reasoning level.
```

Verify:

```bash
cd ~/Projects/27vette
codex --ask-for-approval never "Summarize the current instructions you loaded. Do not edit files."
```

### Step 10: Create Codex Custom Subagents for 27vette

Codex supports subagents and custom agents. The docs say Codex can spawn specialized agents in parallel and consolidate their results; subagents only spawn when explicitly requested. Custom agents are TOML files under `~/.codex/agents/` for personal agents or `.codex/agents/` for project-scoped agents, and each must include `name`, `description`, and `developer_instructions`.

In the repo:

```bash
cd ~/Projects/27vette
mkdir -p .codex/agents
nano .codex/config.toml
```

Paste:

```toml
[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 1800
```

> Keep `max_depth = 1`. Codex docs warn that deeper recursive delegation can increase token use, latency, and predictability risk.

**Create a read-only explorer:**

```bash
nano .codex/agents/vette-explorer.toml
```

```toml
name = "vette_explorer"
description = "Read-only 27vette codebase explorer for mapping files, symbols, data flow, and current behavior before edits."
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Stay read-only.
Map the actual repo evidence:

- Find relevant files, functions, tests, generated artifacts, and workbook-related consumers.
- Cite exact files and symbols.
- Do not propose broad refactors.
- Do not edit files.
- Return concise evidence and unresolved questions.
"""
```

**Create a workbook guardian:**

```bash
nano .codex/agents/workbook-guardian.toml
```

```toml
name = "workbook_guardian"
description = "Read-only 27vette source-of-truth auditor focused on keeping business rules in workbook-authored data."
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Stay read-only.
Audit workbook/source-of-truth implications:

- Identify which workbook source sheet should own a business rule.
- Check whether the issue should be fixed in source data, generator mapping, generated contract, or runtime.
- Flag hardcoded model/RPO exceptions.
- Confirm generated form_* sheets are output surfaces, not hand-edit surfaces.
- For workbook writes, require Excel closed, no lock file, safe save helper, regeneration, and validation.
"""
```

**Create a runtime reviewer:**

```bash
nano .codex/agents/runtime-reviewer.toml
```

```toml
name = "runtime_reviewer"
description = "Read-only reviewer for form-app runtime behavior, model switching, pricing, validation, downloads, and dealer submission risks."
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Stay read-only.
Focus on:

- form-app/app.js behavior paths.
- model switching.
- state transitions.
- rule evaluation.
- pricing.
- download/export behavior.
- dealer submission modal and payload behavior.

Hard boundary:
- Do not change endpoint, payload shape, or Turnstile behavior.
- If runtime logic appears to encode Corvette business rules, recommend workbook/generator ownership instead.
"""
```

**Create an implementation worker:**

```bash
nano .codex/agents/vette-worker.toml
```

```toml
name = "vette_worker"
description = "Implementation-focused 27vette worker for approved, narrow changes only."
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
developer_instructions = """
Only implement an approved spec.
Rules:

- Touch only files named in the approved scope.
- Make the smallest defensible change.
- Do not add dependencies unless explicitly approved.
- Do not refactor unrelated code.
- Do not edit generated workbook form_* sheets directly.
- If a workbook can represent a business rule, do not hardcode it in Python or JavaScript.
- Run the validation gates named in the approved spec.
- Report changed files, unchanged boundaries, gate results, and residual risks.
"""
```

### Step 11: Use Hermes to Generate Codex Prompts

This is the practical "Hermes connects to Codex" workflow:

1. Hermes remembers your project and writes the pass prompt.
2. Codex executes or reviews the pass inside the repo.
3. Git/PR boundaries preserve accountability.

In Hermes:

```
/27vette-pass-plan Write a Codex prompt for a report-only audit of remaining runtime model-specific assumptions in form-app/app.js. Include recommended reasoning level. Do not edit files.
```

Then run the resulting prompt in Codex:

```bash
cd ~/Projects/27vette
codex
```

Prompt Codex:

```
Recommended reasoning level: high
Report-only. Do not edit files.
Use the 27vette AGENTS.md rules. Spawn:

- vette_explorer to map relevant app.js execution paths
- workbook_guardian to classify which assumptions should be workbook-owned
- runtime_reviewer to identify dealer submission, model switching, pricing, and generated contract risks

Wait for all agents. Return:

1. Findings ranked by risk
2. Exact files/symbols involved
3. Which findings belong in workbook data vs generator vs runtime
4. Safest first small implementation pass
5. Validation plan
6. Approval question
```

### Step 12: Use Codex GitHub Review on PRs

After a Hermes/Codex pass creates a PR, use Codex review as the second set of eyes. Codex GitHub review can be requested by commenting `@codex review`; Codex reviews the PR diff, follows repo guidance, and posts a standard GitHub review focused on serious issues.

For 27vette PRs, use targeted review comments:

```
@codex review for workbook source-of-truth violations, hardcoded RPO/model-specific logic, generated artifact drift, dealer submission regressions, and missing validation gates.
```

Codex docs also say you can ask it to fix a P1 issue in the same PR by commenting `@codex fix the P1 issue`, assuming it has permission to push to the branch.

---

## Recommended Hermes Config for 27vette

Edit:

```bash
nano ~/.hermes/profiles/vette-coder/config.yaml
```

Suggested starter:

```yaml
terminal:
  backend: local
  cwd: /Users/seandm/Projects/27vette
  timeout: 300
  env_passthrough: []
approvals:
  mode: manual
  timeout: 60
checkpoints:
  enabled: true
  max_snapshots: 20
  max_total_size_mb: 500
  max_file_size_mb: 10
worktree: false
display:
  tool_progress: new
```

> **Why not YOLO:** Hermes docs warn that YOLO mode bypasses dangerous command prompts except the hardline blocklist. For 27vette, keep manual approvals on. This project has generated artifacts, workbook files, and live-app behavior; a little friction is useful.

---

## Optional MCP Setup

Hermes supports MCP servers for GitHub, filesystem, databases, browser stacks, internal APIs, and other external tools. The docs say MCP servers are configured under `mcp_servers` in `~/.hermes/config.yaml`, and you can filter exposed tools per server.

For 27vette, I would keep MCP minimal at first. Example filesystem-only project scope:

```yaml
mcp_servers:
  project_fs:
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/Users/seandm/Projects/27vette"
```

For GitHub, use a narrow tool whitelist rather than exposing everything:

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_PERSONAL_ACCESS_TOKEN}"
    tools:
      include: [list_issues, create_issue, update_issue]
    prompts: false
    resources: false
```

Hermes docs explicitly recommend per-server filtering as a security control so you expose only the tools you want the model to see.

---

## First Three Practical Workflows to Build

### Workflow 1: Spec-First Pass Planner

Use Hermes:

```
/27vette-pass-plan I want to continue moving Stingray-specific generator/runtime logic into workbook-authored data. Report-only. Do not edit files.
```

Expected output:

- Diagnosis
- Exact files/sheets/artifacts
- Recommended first pass
- Risks and non-goals
- Validation commands
- Approval question

Then feed the approved scope to Codex.

### Workflow 2: Codex Implementation Pass

Use Codex only after the spec is approved:

```
Recommended reasoning level: high
Implement only the approved spec.
Use vette_worker.
Do not touch files outside the approved scope.
Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
Do not edit generated form_* sheets directly.
Run the approved validation gates.
End with:

- files changed
- files intentionally not changed
- commands run and results
- manual verification still needed
- residual risks
```

### Workflow 3: Image Asset Pipeline

Use Hermes first:

```
/27vette-pass-plan Design the RPO image asset pipeline for selectable options. Report-only. Do not edit files. Focus on avoiding duplicate files, missing RPOs, and hardcoded runtime image references.
```

Then Codex gets a narrow task, such as:

```
Recommended reasoning level: medium
Report-only. Do not edit files.
Audit current generated contract and runtime rendering path for where option image metadata could be added. Return:

1. current fields available per choice
2. safest generated data shape for image metadata
3. workbook/source sheet implications
4. first implementation pass
5. validation plan
```

---

## Recommended Division of Labor

**Use Hermes for:**

- remembering the project
- creating 27vette skills
- running checklist-style audits
- phone/messaging access
- recurring reminders or background checks
- worktree orchestration
- writing Codex prompts
- maintaining process discipline

**Use Codex for:**

- focused code edits
- subagent codebase audits
- test-driven implementation
- PR review
- CI failure fixes
- final code-quality checks

---

## Important Caution

Hermes background sessions and messaging access are powerful, but for 27vette I would not let any background/mobile workflow make unattended edits to the repo. The safe pattern is:

| Mode                               | Role                                            |
| ---------------------------------- | ----------------------------------------------- |
| **phone/mobile Hermes**            | report-only, planning, audit, prompt generation |
| **local Hermes/Codex in worktree** | implementation                                  |
| **GitHub PR + Codex review**       | final review layer                              |

That keeps the live order-form app, workbook, generated artifacts, and dealer submission path protected while still giving you the benefit of a persistent agent that can remember how this project works.

---

## Condensed Instruction

Hermes can reference `spec-review/hermes-onboarding.md`, but it will not auto-load that file just because it exists. Hermes auto-loads project context files like `.hermes.md`, `HERMES.md`, or `AGENTS.md`; normal markdown files must be explicitly read or referenced in the prompt. Hermes treats `AGENTS.md` as the main project context file, and `.hermes.md`/`HERMES.md` have higher priority if present.

### Do This First

```bash
cd ~/Projects/27vette
git status
hermes doctor
```

If `git status` is not clean, stop and decide whether to commit/stash first.

### Create a Dedicated Hermes Profile for 27vette

Hermes profiles are separate agent homes with their own config, memory, sessions, skills, and state.

```bash
hermes profile create vette-coder --clone
vette-coder setup
vette-coder config set terminal.cwd "$PWD"
```

Check it:

```bash
vette-coder doctor
vette-coder profile
```

### Use Worktree Mode for Actual Repo Edits

Hermes recommends worktrees so each agent session has its own branch/checkout.

From the 27vette repo root:

```bash
cd ~/Projects/27vette
vette-coder -w
```

For report-only setup work, normal mode is fine:

```bash
cd ~/Projects/27vette
vette-coder chat
```

### Let Hermes Set Itself Up From Your Onboarding File

Run this from the repo root:

```bash
cd ~/Projects/27vette
vette-coder chat --checkpoints
```

Then paste this prompt:

```
Read these files first:

- AGENTS.md
- codex-context.md
- spec-review/hermes-onboarding.md

Task: Set up my Hermes workspace for 27vette.
Report your plan first. Do not edit code files.

Allowed setup changes:
- Create or update Hermes skills under the vette-coder Hermes profile.
- Create a concise 27vette Hermes memory note if appropriate.
- Recommend, but do not create, any repo-level .hermes.md unless you explain why it is needed.
- Do not change app code, workbook files, generated artifacts, form-output files, form-app/data.js, package/dependency files, or dealer submission behavior.

Create these skills if appropriate:
1. 27vette-pass-plan
2. 27vette-workbook-guard
3. 27vette-gate
4. 27vette-codex-prompt
5. 27vette-image-audit

For each skill, keep it short and practical:
- when to use
- exact procedure
- output format
- validation/gate expectations

After setup, show:
- files created/changed
- where the skills live
- how to invoke each skill
- anything you intentionally did not change
```

> Hermes checkpoints are useful here because they snapshot before file writes and allow rollback.

### Manual Fallback: Create the Skills Yourself

Hermes skills live under `~/.hermes/skills/` and become slash commands.

Use this if you want to create only the essentials manually:

```bash
mkdir -p ~/.hermes/profiles/vette-coder/skills/dev/27vette-pass-plan
nano ~/.hermes/profiles/vette-coder/skills/dev/27vette-pass-plan/SKILL.md
```

Paste:

```markdown
---
name: 27vette-pass-plan
description: Spec-first planning workflow for 27vette development passes.
version: 1.0.0
metadata:
  hermes:
    category: dev
    tags: [27vette, corvette, workbook, planning]
---

# 27vette Pass Plan

## When to Use

Use before any non-trivial 27vette change.

## Procedure

1. Read AGENTS.md and codex-context.md.
2. Determine scope: report-only, docs-only, workbook/data-only, generator-only, runtime-only, test-only, or mixed.
3. Identify exact files, workbook sheets, generated artifacts, and tests.
4. Decide whether the issue belongs in workbook data, generator logic, runtime logic, or tests.
5. Reject hardcoded RPO/model exceptions unless explicitly approved.
6. Produce a spec before edits.

## Output

- Diagnosis
- Proposed scope
- Files/sheets/artifacts affected
- Risks and non-goals
- Validation plan
- Approval question

## Hard Rules

- Business rules belong in workbook-authored data when possible.
- Do not edit generated form_* sheets directly.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior without approval.
- Keep passes small.
```

Invoke it:

```
/27vette-pass-plan Plan the next safe pass for cleaning up 27vette. Report-only.
```

### Recommended Skill List

Create these only after the first one works:

| Skill | Purpose |
|---|---|
| `/27vette-pass-plan` | Spec-first pass planning. |
| `/27vette-workbook-guard` | Decide whether a fix belongs in workbook data, generator code, runtime JS, or tests. |
| `/27vette-gate` | Choose and run the right validation commands. |
| `/27vette-codex-prompt` | Write tight Codex prompts with recommended reasoning level. |
| `/27vette-image-audit` | RPO image coverage, duplicates, missing images, and asset-map planning. |

> **Important:** Do not add `.hermes.md` yet. Your repo already has `AGENTS.md`, and Hermes will load it automatically. Adding `.hermes.md` would outrank `AGENTS.md`, which could create conflicting instruction layers.
