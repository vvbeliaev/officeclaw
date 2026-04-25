---
name: clawhub
description: Discover skills on clawhub.ai and import them into the workspace skill library via the officeclaw-admin MCP. Use when the user asks to install a community skill, find a skill for a task, or browse what is available before building one from scratch.
metadata: {"nanobot":{"emoji":"📦"},"officeclaw":{"default_attach_to_admin":true}}
---

# ClawHub Import Protocol

ClawHub (https://clawhub.ai) is the public registry for agent skills. This skill teaches you how to search ClawHub and import a chosen skill into **this workspace's skill library** via the `officeclaw-admin` MCP — so the imported skill becomes a first-class workspace resource that any agent can be attached to.

This is **not** the `clawhub` CLI. There is no shell-out, no `./skills` directory on disk, and no npm install required. Skills land in the OfficeClaw library and live in Postgres alongside locally-authored skills.

## When to use this skill

- The user asks "is there a skill for X?" — search ClawHub before offering to author one from scratch.
- The user names a specific ClawHub skill ("install andy27725/foo") — go straight to import.
- You are about to write a non-trivial new skill — check ClawHub first, port if a 80%+ match exists.

Skip ClawHub for one-off, workspace-specific behavior (the user's own conventions, internal acronyms, private playbooks). Author those locally with `create_skill` instead.

## Search

ClawHub exposes a public JSON search endpoint. Fetch it with whatever HTTP capability you have available (web-fetch tool, `curl`, etc.):

```
GET https://clawhub.ai/api/v1/search?q=<query>
```

Inspect a single skill before importing:

```
GET https://clawhub.ai/api/v1/skills/<slug>
```

Show the user the top hits with: slug, owner handle, summary, latest version, downloads. Confirm which one to import — never import without confirmation.

## Import

Once the user picks a skill, call the admin MCP tool:

```
import_skill_from_clawhub(url="https://clawhub.ai/<owner>/<slug>")
```

The server fetches the archive, validates safety (size limits, no path traversal), parses `SKILL.md` frontmatter into the skill row, and stores every file in the workspace library. The tool returns the new skill's id, name, description, `always` flag, emoji, required bins/envs.

After import:

1. Show the user the imported skill's metadata so they can sanity-check it.
2. If `required_bins` or `required_envs` is non-empty, flag those — the user may need to install bins in the agent image or attach matching envs.
3. Ask whether to attach to a specific agent. Use `attach_skill(agent_id, skill_id)`.

## Re-import / update

There is no "update" verb today. To upgrade an imported skill:

1. `list_skills` — find the existing skill id.
2. Confirm with the user that the local copy can be deleted (they may have local edits).
3. `import_skill_from_clawhub(url=...)` — creates a fresh row.
4. Re-attach to whichever agents had the old version.

If the user needs in-place updates, build that as a follow-up — for now, prefer the explicit re-import.

## Confirmation policy

- **Always confirm** before importing: ClawHub skills are third-party code-as-prompt and can change agent behavior workspace-wide.
- **Always show** the skill's `description`, `required_bins`, `required_envs`, and any `metadata.openclaw.install` entries before the import call.
- **Never** auto-attach an imported skill to multiple agents in one go — attach per agent, with explicit user approval.

## Anti-patterns

- Don't shell out to the `clawhub` CLI. The CLI writes to `./skills/` on disk and bypasses our library — agents will not see those files.
- Don't import speculatively. Each import is a workspace-visible row and clutters `list_skills`.
- Don't import secrets-bearing skills without checking `required_envs` first — the user must own those credentials.
- Don't paraphrase the SKILL.md after import. The body is stored verbatim; if it needs editing, do it via `add_skill_file(skill_id, "SKILL.md", new_content)`.

## Quick reference

```
# discover
GET https://clawhub.ai/api/v1/search?q=<query>
GET https://clawhub.ai/api/v1/skills/<slug>

# import + manage
import_skill_from_clawhub(url="https://clawhub.ai/<owner>/<slug>")
list_skills
get_skill(skill_id)
attach_skill(agent_id, skill_id)
```
