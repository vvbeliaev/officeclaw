# OfficeClaw Design System

## Direction: Warm Studio

OfficeClaw isn't another hacker tool. It's the agent manager for people who want their AI workforce to work — the writer who wants a research assistant, the entrepreneur who needs agents running admin tasks, the developer who refuses to be locked into anyone's platform. Open. Yours. Controllable.

The visual identity is built on a single idea: **a warm, well-made studio**. Not a terminal simulator, not a SaaS startup template — something with the feel of a thoughtfully designed workspace: warm light, natural materials, calm precision. Approachable for non-technical users. Comfortable to live in.

**The one thing people remember:** Generous, warm typography set against deep warm charcoal, lit by amber or sage. Nobody in the agent-tool space feels like this.

---

## 1. Atmosphere

**Dark canvas — warm charcoal.**
Not cold blue-void (too enterprise, too clinical). Not pure black (too aggressive). The OKLCH hue ~55–60 (warm brown-charcoal axis) reads as *depth and comfort* — like a well-lit studio at night, quality wood, something lived-in and trusted. `oklch(0.13 0.018 55)` is the base.

**Accent — two options, pick one per deployment:**

**Option A: Claw Amber (current, recommended)**
`oklch(0.80 0.145 72)` — slightly softer than before, golden rather than sharp. Warm, focused. Still the best choice in the space.

**Option B: Sage Green (experiment)**
`oklch(0.72 0.13 148)` — warm eucalyptus sage. Not hacker green (too cold, too aggressive) — this reads as natural, calm, grounded. Think Notion's warmth meets garden-studio aesthetic. Beautiful against warm charcoal.

Status green (for running agents) shifts to `oklch(0.70 0.16 148)` in the amber variant, or becomes the primary in the sage variant (use `oklch(0.68 0.17 155)` for running status instead).

**Type — three voices, warmth over sharpness.**
- *Display:* Fraunces — optical-size serif, warm and distinctive, weight-driven emphasis (no italic required). Reads beautifully at large sizes, feels human and editorial without being aggressive.
- *Body:* Plus Jakarta Sans Variable — geometric warmth, slightly more rounded than DM Sans, very approachable for non-coders. Variable weight 300–700.
- *Mono:* DM Mono — unchanged, cohesive for logs and agent IDs.

**Icons — custom `oc:` collection.**
14 bespoke stroke-based icons built specifically for the fleet-management vocabulary: `oc:agent`, `oc:fleet`, `oc:claw`, `oc:tool`, `oc:memory`, `oc:running`, `oc:idle`, `oc:stopped`, `oc:error`, `oc:pending`, `oc:configure`, `oc:log`, `oc:spawn`, `oc:open`. Use via `@iconify/svelte` with `addCollection`.

---

## 2. Color System

### Dark Mode (primary interface)

#### Option A: Amber accent (warm charcoal base)

| Token | OKLCH | Approximate |
|---|---|---|
| Background | `oklch(0.13 0.018 55)` | Warm deep charcoal |
| Card | `oklch(0.18 0.014 55)` | Elevated warm surface |
| Popover | `oklch(0.21 0.013 55)` | Floating layer |
| Secondary / Hover | `oklch(0.23 0.012 55)` | Subtle warm fill |
| Border | `oklch(1 0 0 / 8%)` | Transparent white |
| Input | `oklch(1 0 0 / 12%)` | Form field |
| Foreground | `oklch(0.95 0.008 80)` | Warm near-white |
| Muted foreground | `oklch(0.58 0.012 55)` | Warm mid-tone |
| **Primary (Amber)** | `oklch(0.80 0.145 72)` | Claw Amber — softer gold |
| Primary fg | `oklch(0.12 0.018 55)` | Dark on amber |
| Destructive | `oklch(0.64 0.21 25)` | Coral red — errors |
| Ring | `oklch(0.80 0.145 72 / 40%)` | Amber focus ring |

#### Option B: Sage Green accent (warm charcoal base)

| Token | OKLCH | Approximate |
|---|---|---|
| Background | `oklch(0.13 0.018 55)` | Warm deep charcoal (same) |
| Card | `oklch(0.18 0.014 55)` | Elevated warm surface |
| Popover | `oklch(0.21 0.013 55)` | Floating layer |
| Secondary / Hover | `oklch(0.23 0.012 55)` | Subtle warm fill |
| Border | `oklch(1 0 0 / 8%)` | Transparent white |
| Input | `oklch(1 0 0 / 12%)` | Form field |
| Foreground | `oklch(0.95 0.008 80)` | Warm near-white |
| Muted foreground | `oklch(0.60 0.014 130)` | Warm sage-tinted mid |
| **Primary (Sage)** | `oklch(0.72 0.13 148)` | Warm eucalyptus sage |
| Primary fg | `oklch(0.12 0.018 55)` | Dark on sage |
| Destructive | `oklch(0.64 0.21 25)` | Coral red — errors |
| Ring | `oklch(0.72 0.13 148 / 40%)` | Sage focus ring |

### Light Mode (marketing / onboarding)

| Token | OKLCH | Role |
|---|---|---|
| Background | `oklch(0.985 0.008 80)` | Warm cream paper |
| Card | `oklch(0.975 0.010 80)` | Slightly warmer paper |
| Foreground | `oklch(0.14 0.018 55)` | Warm charcoal text |
| Primary (Amber) | `oklch(0.62 0.145 72)` | Deeper amber on light |
| Primary (Sage) | `oklch(0.52 0.13 148)` | Deeper sage on light |
| Border | `oklch(0.875 0.012 80)` | Warm cream separator |
| Muted fg | `oklch(0.52 0.014 55)` | Warm secondary text |

### Agent Status Colors

| Status | Color | OKLCH |
|---|---|---|
| Running | Mint green | `oklch(0.70 0.17 148)` |
| Idle | Warm slate | `oklch(0.55 0.010 55)` |
| Error | Coral | `oklch(0.65 0.21 25)` |
| Stopped | Dark muted | `oklch(0.38 0.008 55)` |
| Pending | Sky blue | `oklch(0.72 0.12 220)` |

Note: Amber/Sage are **not** status colors — they're the brand CTA. Running always uses green (semantic "go").

---

## 3. Typography

### Three Voices

| Voice | Family | Role |
|---|---|---|
| Display | `Fraunces` 300–800 (opsz) | Hero titles, section headings — weight emphasis, no italic needed |
| Body | `Plus Jakarta Sans Variable` 300–700 | All UI text, labels, descriptions |
| Mono | `DM Mono` 400/500 | Agent IDs, logs, config values, timestamps |

### Display — Fraunces

The identity choice. Variable optical-size font (opsz axis 9–144) — heavier at small sizes, elegant at large. Use weight 700–800 at `text-4xl` and above. Optical adjustments happen automatically.

```css
.display { 
  font-family: var(--font-display); 
  font-variation-settings: 'opsz' 72, 'wght' 750;
  letter-spacing: -0.025em;
  line-height: 1.08;
}
```

**No italic dependency** — differentiation comes from weight and optical size, not slant. Feels warm and human without the aggression of narrow italic serifs.

Tracking: `-0.025em` at display sizes. Line-height: `1.08`–`1.12` for tight impactful blocks.

### Body — Plus Jakarta Sans Variable

- `font-feature-settings: "cv01", "ss01", "kern"` globally
- Weight 400 body, 500 labels/nav, 600 emphasis
- Letter-spacing `0.01em` on uppercase micro-labels
- Slightly more generous line-height than DM Sans: `1.6` for body, `1.4` for UI

### Mono — DM Mono

- Agent IDs always mono: `#AGT-001`
- Log timestamps, status codes, config keys
- Slightly smaller than body: `text-[0.8125rem]` for inline technical labels

### Scale — go larger

Base body: `16px` (not 14px). UI feels more breathable and approachable.

| Scale | Size | Usage |
|---|---|---|
| `text-xs` | 12px | Timestamps, secondary metadata |
| `text-sm` | 14px | Table data, small labels |
| `text-base` | 16px | Body text (baseline) |
| `text-lg` | 18px | Emphasized body, descriptions |
| `text-xl` | 20px | Section subtitles |
| `text-2xl` | 24px | Page titles, card headers |
| `text-3xl` | 30px | Hero sub-headings |
| `text-4xl` | 36px | Hero headings |
| `text-5xl+` | 48px+ | Landing display only |

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

### Border Radius — softer throughout

| Context | Value | Tailwind |
|---|---|---|
| Status dot | 50% | `rounded-full` |
| Badge, chip | 6px | `rounded-md` |
| Input, row, small card | 8px | `rounded-lg` |
| Card | 14px | `rounded-2xl` |
| Dialog/Modal | 18px | use inline |
| Primary CTA (pill) | 9999px | `rounded-full` |

Everything is ~40% more rounded than before — feels softer, less aggressive.

### Spacing — more generous

Base unit 4px. Key spacings: padding-x on cards `p-5` (20px) vs old `p-4`. Section gaps `gap-6` to `gap-8`. Let the interface breathe.

### Elevation (shadow-as-depth)

```css
/* E1 — row / subtle */
box-shadow: 0 1px 3px oklch(0.05 0.018 55 / 0.35), 0 0 0 1px oklch(1 0 0 / 0.06);

/* E2 — card */
box-shadow: 0 4px 20px oklch(0.05 0.018 55 / 0.50), 0 1px 4px oklch(0.05 0.018 55 / 0.30), 0 0 0 1px oklch(1 0 0 / 0.08);

/* E3 — modal */
box-shadow: 0 24px 64px oklch(0.05 0.018 55 / 0.70), 0 4px 16px oklch(0.05 0.018 55 / 0.40), 0 0 0 1px oklch(1 0 0 / 0.10);

/* Amber glow — primary CTA */
box-shadow: 0 0 24px oklch(0.80 0.145 72 / 22%);

/* Sage glow — primary CTA (Option B) */
box-shadow: 0 0 24px oklch(0.72 0.13 148 / 20%);

/* Green glow — running agent card */
box-shadow: 0 0 0 1px oklch(0.70 0.17 148 / 20%), 0 0 24px oklch(0.70 0.17 148 / 7%);
```

---

## 6. Motion

Warm and eased, not snappy or aggressive. Physical deceleration.

```css
transition: 180ms cubic-bezier(0.4, 0, 0.2, 1);  /* standard */
transition: 250ms cubic-bezier(0.16, 1, 0.3, 1);   /* reveal/entrance */
animation: status-pulse 3s ease-in-out infinite;    /* running dot — slower = calmer */
```

---

## 7. The Voice

**Headlines (Fraunces 750, weight-emphasis):** Short, warm, declarative.
- *Your agents, working.*
- *Spawn in seconds.*
- *No lock-in. Ever.*

**Body (Plus Jakarta Sans):** Plain English. No jargon barriers.

**Labels (Plus Jakarta Sans 500, uppercase 0.08em tracking):** `RUNNING · 4 TASKS · 2H UPTIME`

**Mono (DM Mono):** `#AGT-001` `claude-sonnet-4-6` `14:32:01 INFO`

---

## 8. Differentiation from Similar Tools

| Tool | Their aesthetic | Our differentiation |
|---|---|---|
| VoltAgent | Hacker green on void-black | Warm charcoal, weight-based serif — approachable |
| OpenCode | Dark dev-centric | Warm studio atmosphere, non-coders feel welcome |
| Linear | Purple accent, ultra-minimal | Warmer, more human, more texture |
| Supabase | Emerald on deep dark | Different temperature, Fraunces personality |
| Raycast | MacOS precision | Warmer, rounder, more inviting |

**OfficeClaw's space:** The only agent manager that a non-technical founder would open and immediately feel comfortable in — while still earning the trust of technical users.

---

## 9. Design Sources

| Ref | What we took |
|---|---|
| **Fraunces / OH no Type** | Optical serif warmth, weight-driven personality without italic |
| **Notion** | Approachability, neutral warmth that welcomes non-tech users |
| **Linear** | Opacity hierarchy in dense data views, border precision |
| **Warp** | Warmth direction — how dark can still feel inviting |
| **Raycast** | Precision instrument personality, physical depth shadows |
| **Vercel** | Shadow-as-border technique, lifecycle state color logic |
| **HashiCorp** | CSS var token architecture, multi-type color system |
| **Supabase** | OKLCH token system, CTA pill vs radius hierarchy |

---

## 10. Font Loading

```html
<!-- In <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300..800&family=Plus+Jakarta+Sans:wght@300..700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-mono: 'DM Mono', 'Fira Mono', monospace;
}
```
