# OfficeClaw Design System

## Direction: Open Craft

OfficeClaw isn't another hacker tool. It's the agent manager for people who want their AI workforce to work — the writer who wants a research assistant, the entrepreneur who needs agents running admin tasks, the developer who refuses to be locked into anyone's platform. Open. Yours. Controllable.

The visual identity is built on a single idea: **a well-made instrument**. Not a terminal simulator, not a SaaS startup template — something with the craft of a premium printed artifact and the precision of a piece of hardware you trust.

**The one thing people remember:** Instrument Serif italic headlines against cool ink-dark slate, lit by amber warmth. Nobody in the agent-tool space looks like this.

---

## 1. Atmosphere

**Dark canvas — deep ink-slate.**
Not brown (too warm, too cozy, excludes), not cold blue-void (too clinical, says "enterprise"). The OKLCH hue ~240 (blue-slate axis) creates depth that reads as *authority and precision* — like a good quality notebook, a carbon fiber surface, something built. `oklch(0.12 0.014 242)` is the base.

**Accent — Claw Amber.**
A single warm amber (`oklch(0.80 0.155 68)`) against the cool dark creates maximum warmth contrast. It says: there's a human here. Nobody in the AI-agent space uses amber — emerald is taken (VoltAgent, Supabase), purple is taken (Linear, Stripe), orange is too loud. Amber is warm, focused, like a lit lamp on a desk. The perfect color for "your agents, working."

**Type — three voices, no Inter.**
- *Display:* Instrument Serif — editorial, crafted, italic headings look extraordinary
- *Body:* DM Sans Variable — geometric warmth, approachable for non-coders
- *Mono:* DM Mono — sister font, cohesive family, for logs and agent IDs

**Icons — custom `oc:` collection.**
14 bespoke stroke-based icons built specifically for the fleet-management vocabulary: `oc:agent`, `oc:fleet`, `oc:claw`, `oc:tool`, `oc:memory`, `oc:running`, `oc:idle`, `oc:stopped`, `oc:error`, `oc:pending`, `oc:configure`, `oc:log`, `oc:spawn`, `oc:open`. Use via `@iconify/svelte` with `addCollection`.

---

## 2. Color System

### Dark Mode (primary interface)

| Token | OKLCH | Approximate |
|---|---|---|
| Background | `oklch(0.12 0.014 242)` | Deep ink-slate |
| Card | `oklch(0.17 0.012 242)` | Elevated surface |
| Popover | `oklch(0.20 0.012 242)` | Floating layer |
| Secondary / Hover | `oklch(0.22 0.012 242)` | Subtle fill |
| Border | `oklch(1 0 0 / 9%)` | Transparent white |
| Input | `oklch(1 0 0 / 13%)` | Form field |
| Foreground | `oklch(0.94 0.010 90)` | Warm near-white |
| Muted foreground | `oklch(0.58 0.014 242)` | Cool mid-slate |
| **Primary (Amber)** | `oklch(0.80 0.155 68)` | Claw Amber — CTAs, active |
| Primary fg | `oklch(0.12 0.014 242)` | Dark on amber |
| Destructive | `oklch(0.64 0.21 25)` | Coral red — errors |
| Ring | `oklch(0.80 0.155 68 / 45%)` | Amber focus ring |

### Light Mode (marketing / onboarding)

| Token | OKLCH | Role |
|---|---|---|
| Background | `oklch(0.985 0.006 88)` | Warm paper |
| Card | `oklch(0.975 0.008 88)` | Slightly warmer paper |
| Foreground | `oklch(0.14 0.015 240)` | Ink-slate text |
| Primary | `oklch(0.62 0.155 68)` | Darker amber (light surface) |
| Border | `oklch(0.878 0.010 88)` | Warm paper separator |
| Muted fg | `oklch(0.52 0.016 240)` | Cool secondary text |

### Agent Status Colors

| Status | Color | OKLCH |
|---|---|---|
| Running | Mint green | `oklch(0.72 0.18 145)` |
| Idle | Cool slate | `oklch(0.55 0.012 242)` |
| Error | Coral | `oklch(0.65 0.21 25)` |
| Stopped | Dark muted | `oklch(0.38 0.010 242)` |
| Pending | Sky blue | `oklch(0.72 0.12 220)` |

Note: Amber is **not** a status color — it's the brand CTA. Running uses green (semantic "go"), everything else avoids the amber channel.

---

## 3. Typography

### Three Voices

| Voice | Family | Role |
|---|---|---|
| Display | `Instrument Serif` 400/400i | Hero titles, section headings (italic for emphasis) |
| Body | `DM Sans Variable` 300–600 | All UI text, labels, descriptions |
| Mono | `DM Mono` 400/500 | Agent IDs, logs, config values, timestamps |

### Display — Instrument Serif

The identity choice. At `text-4xl` and above, use italic for section callouts — `*Your agents, working.*` This is the one font choice nobody else in this space makes. It signals craft, seriousness, and human attention.

```css
.display-italic { font-family: var(--font-display); font-style: italic; }
```

Tracking: `-0.03em` at display sizes. Line-height: `1.1`–`1.15` for tight impactful blocks.

### Body — DM Sans Variable

- `font-feature-settings: "cv01", "ss01", "kern"` globally
- Weight 400 body, 500 labels/nav, 600 emphasis
- Letter-spacing `0.01em` on uppercase micro-labels

### Mono — DM Mono

- Agent IDs always mono: `#AGT-001`
- Log timestamps, status codes, config keys
- Slightly smaller than body: `text-[0.8125rem]` for inline technical labels

---

## 4. Icons — `oc:` Collection

Custom Iconify collection at `src/lib/icons/oc.json`. Register on app init via `addCollection` from `@iconify/svelte`.

| Icon | Usage |
|---|---|
| `oc:agent` | Single agent representation |
| `oc:fleet` | Fleet/overview view |
| `oc:claw` | Brand mark, favicon |
| `oc:tool` | Tools & capabilities |
| `oc:memory` | Memory / knowledge base |
| `oc:running` | Running status |
| `oc:idle` | Idle status |
| `oc:stopped` | Stopped status |
| `oc:error` | Error status |
| `oc:pending` | Pending/queued status |
| `oc:configure` | Configuration sliders |
| `oc:log` | Log/output view |
| `oc:spawn` | Create/spawn new agent |
| `oc:open` | Open-source / no lock-in identity |

Usage: `<Icon icon="oc:agent" class="size-5" />`

---

## 5. Spacing, Radius, Depth

### Border Radius

| Context | Value | Tailwind |
|---|---|---|
| Status dot | 50% | `rounded-full` |
| Badge, chip | 4px | `rounded` |
| Input, row, small card | 6px | `rounded-md` |
| Card | 10px | `rounded-xl` |
| Dialog/Modal | 14px | use inline |
| Primary CTA (pill) | 9999px | `rounded-full` |

### Elevation (shadow-as-depth)

```css
/* E1 — row / subtle */
box-shadow: 0 1px 2px oklch(0.05 0.014 242 / 0.4), 0 0 0 1px oklch(1 0 0 / 0.07);

/* E2 — card */
box-shadow: 0 4px 16px oklch(0.05 0.014 242 / 0.55), 0 1px 3px oklch(0.05 0.014 242 / 0.35), 0 0 0 1px oklch(1 0 0 / 0.09);

/* E3 — modal */
box-shadow: 0 20px 60px oklch(0.05 0.014 242 / 0.75), 0 4px 16px oklch(0.05 0.014 242 / 0.45), 0 0 0 1px oklch(1 0 0 / 0.11);

/* Amber glow — primary CTA */
box-shadow: 0 0 20px oklch(0.80 0.155 68 / 25%);

/* Green glow — running agent card */
box-shadow: 0 0 0 1px oklch(0.72 0.18 145 / 22%), 0 0 24px oklch(0.72 0.18 145 / 8%);
```

---

## 6. Motion

Snap, don't float. Physical deceleration.

```css
transition: 150ms cubic-bezier(0.4, 0, 0.2, 1);  /* standard */
transition: 200ms cubic-bezier(0.16, 1, 0.3, 1);   /* reveal/entrance */
animation: status-pulse 2.5s ease-in-out infinite;  /* running dot */
```

---

## 7. The Voice

**Headlines (Instrument Serif italic):** Short, declarative, human.
- *Your agents, working.*
- *Spawn in seconds.*
- *No lock-in. Ever.*

**Body (DM Sans):** Plain English. No jargon barriers.

**Labels (DM Sans 500, uppercase 0.08em tracking):** `RUNNING · 4 TASKS · 2H UPTIME`

**Mono (DM Mono):** `#AGT-001` `claude-sonnet-4-6` `14:32:01 INFO`

---

## 8. Differentiation from Similar Tools

| Tool | Their aesthetic | Our differentiation |
|---|---|---|
| VoltAgent | Hacker green on void-black | Amber warmth, editorial type — approachable |
| OpenCode | Dark dev-centric | Serif personality, richer typography system |
| Linear | Purple accent, ultra-minimal | More warmth, human-first not engineer-first |
| Supabase | Emerald on deep dark | Different temperature, serif editorial voice |
| Raycast | MacOS precision | Warmer, more inviting to non-power users |

**OfficeClaw's space:** The only agent manager that feels like it was *designed*, not just implemented.

---

## 9. Design Sources

| Ref | What we took |
|---|---|
| **VoltAgent** | Single-accent discipline, dark canvas conviction |
| **Cursor** | Three-font system, editorial typography ambition |
| **Linear** | Opacity hierarchy in dense data views, border precision |
| **Warp** | Warmth direction — how dark can still feel inviting |
| **Raycast** | Precision instrument personality, physical depth shadows |
| **Vercel** | Shadow-as-border technique, lifecycle state color logic |
| **HashiCorp** | CSS var token architecture, multi-type color system |
| **Supabase** | OKLCH token system, CTA pill vs radius hierarchy |
