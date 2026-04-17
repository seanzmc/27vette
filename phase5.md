Use the 27vette skill.

Refine mutually exclusive option logic.

Focus on:
- Choice Groups
- Choice Group Members
- Option Catalog
- Option Rules
- Variant Choice Availability
- Audit Exceptions

Tasks:
1. Confirm or create explicit choice groups for categories such as:
   - seats
   - interior colors
   - exterior colors
   - wheels
   - aero or appearance groups if applicable
2. Ensure each group has a stable choice_group_id.
3. Ensure members are linked by option_id rather than only labels.
4. Build Variant Choice Availability so each variant shows which members are available, default, blocked, or conditional.
5. Record unresolved ambiguity in Audit Exceptions.

Summarize:
- which groups are complete
- which groups are still fuzzy
- which options are currently members of multiple groups or no group
