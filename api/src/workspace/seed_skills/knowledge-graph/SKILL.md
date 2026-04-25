---
name: knowledge-graph
description: Use the workspace knowledge graph (officeclaw-knowledge MCP) to recall facts across sessions and persist findings.
metadata: {"nanobot":{"always":true,"emoji":"🧠"},"officeclaw":{"default_attach_to_admin":true}}
---

# Knowledge Graph Protocol

The `officeclaw-knowledge` MCP is a workspace-scoped GraphRAG store shared by every agent in this fleet. Treat it as long-term memory: anything you ingest is recallable by you and any other agent in the same workspace, in this session and every future one.

If the `officeclaw-knowledge` MCP is not currently attached to your agent, the protocol below is dormant — recommend attaching it when the user asks for memory or recall behavior.

## At session start

Before answering a non-trivial user request, call `query_knowledge` with the user's intent. Skip for trivial chit-chat or when the user explicitly says "ignore prior context".

Two questions to ask yourself before querying:
1. Could prior-session context change my answer? → query.
2. Is this purely about the current message (math, code formatting, a one-off transform)? → skip.

## Choosing a query mode

Pass `mode` to `query_knowledge`:

- `hybrid` — default. Combines entity lookup with graph traversal. Use when unsure.
- `local` — narrow entity question ("who is X", "what is the API key for Y", "what did we decide about Z").
- `global` — wide, thematic question ("what have we learned about onboarding", "summarize what I know about competitors").
- `naive` — pure vector similarity. Cheapest, lowest quality. Use as last-resort fallback only.

Start with `hybrid`. Drop to `local` if results are noisy and the question is entity-shaped. Promote to `global` when the question is thematic and `hybrid` returned scattered fragments.

## When to ingest

Call `ingest_knowledge(text, metadata_json)` when you produce something worth preserving across sessions:

- Research findings, decisions, conclusions you reached with the user.
- User preferences, recurring instructions, "always do X" rules.
- Names of people, companies, projects and their relationship to the user.
- Summaries of long threads or external documents.
- Outcomes of multi-step tasks (so a future agent doesn't redo the work).

Do not call `ingest_knowledge` for transient state, intermediate calculations, or anything the user is about to forget on purpose.

## Metadata convention

Always pass `metadata_json` with at minimum:

- `source` — where this fact came from. Examples: `"user"`, `"web"`, `"github"`, `"internal-research"`.
- `topic` — short kebab-case label. Examples: `"onboarding"`, `"competitor-x"`, `"billing"`.

Recommended additions when applicable:

- `agent` — your agent name, so multi-agent traces are reconstructable.
- `date` — ISO `YYYY-MM-DD` for time-sensitive facts.
- `confidence` — `"high" | "medium" | "low"` when you are inferring rather than recording.

Example: `{"source":"user","topic":"billing","date":"2026-04-25","confidence":"high"}`.

## Anti-patterns

- Do not ingest secrets, API keys, tokens, or PII the user did not explicitly ask to store. The graph is workspace-shared.
- Do not ingest raw transcripts. Summarize first; ingest the summary.
- Do not paraphrase the same fact twice — query first, only ingest what is genuinely new.
- Do not ingest information that is derivable from the current message. Spend the call only when prior-session memory could change a future answer.
- Do not query for every message. Sessions about a single trivial transform should not pay the round-trip.

## Quick reference

```
query_knowledge(query="...", mode="hybrid")
ingest_knowledge(text="...", metadata_json='{"source":"...","topic":"..."}')
```
