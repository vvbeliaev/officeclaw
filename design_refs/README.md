# OfficeClaw — Design References

OfficeClaw is an **AI agent fleet manager**: users spawn, configure, and monitor a personal fleet of AI agents. The UI lives at the intersection of infrastructure tooling and AI developer experience. Think: control room, not dashboard. Terminal, not form.

Eight references were selected from [getdesign.md](https://getdesign.md) — covering color language, information density, typography, interaction patterns, and surface depth.

---

## References

### [voltagent.md](./voltagent.md) — Foundation / Atmosphere
> "Void-black canvas, emerald accent, terminal-native"

The closest conceptual match — VoltAgent *is* an AI agent framework. Its carbon-black canvas (`#050507`), single emerald accent (`#00d992`), warm-gray neutrals, and "code snippets as hero content" philosophy directly maps to OfficeClaw's identity. The pulsing green glow effect on interactive elements visually communicates "agent active."

**Contributes to OfficeClaw:**
- Base dark theme and canvas color
- Accent color logic (single chromatic energy source)
- Warm-gray text hierarchy (`#f2f2f2` → `#b8b3b0` → `#8b949e`)
- Green glow on active/running agents

---

### [hashicorp.md](./hashicorp.md) — Fleet Architecture / Token System
> "Infrastructure automation, enterprise-clean, black and white"

HashiCorp manages infrastructure *fleets* — its design system solves the same visual problem OfficeClaw faces: representing multiple agent types with distinct identities inside a unified interface. Their multi-product color system (`--mds-color-terraform`, `--mds-color-vault`) is the exact pattern for agent-type color tokens. Tight 2–8px border radii, semantic CSS variables, and micro-shadow depth communicate production-grade reliability.

**Contributes to OfficeClaw:**
- Agent-type color token pattern (each agent type gets a color identity)
- CSS custom property architecture (`--agent-color-*`)
- Tight border radii — no rounded pill shapes in infrastructure UI
- Dual-mode layout: light for docs/onboarding, dark for live fleet views
- Enterprise typography weight and density

---

### [linear.app.md](./linear.app.md) — Fleet Monitoring UI
> "Ultra-minimal, precise, purple accent"

Linear's near-black dark mode with opacity-only hierarchy is the reference for OfficeClaw's agent list and monitoring views — where dozens of agents need visual scanning without color noise. Signature weight 510, semi-transparent white borders (`rgba(255,255,255,0.05)`), and Berkeley Mono for technical identifiers define the density model.

**Contributes to OfficeClaw:**
- Agent list/table density and row hierarchy
- Opacity-based UI hierarchy (no bright colors in data rows)
- Berkeley Mono for agent IDs, timestamps, technical labels
- Status indicators using the minimal success-green pattern
- Shadow system for elevated panels (card-in-dark-background)

---

### [cursor.md](./cursor.md) — Premium Warmth / Landing Page
> "Warm minimalism meets code-editor elegance"

Cursor is the *counter-reference* — it runs light/warm while the others run dark/cool. OfficeClaw's marketing page and onboarding flow benefit from Cursor's warm cream canvas, editorial serif counterpoint, and high-craft typographic texture. The three-font system concept (display + body + mono) is directly applicable.

**Contributes to OfficeClaw:**
- Landing / marketing page surface (warm cream, not cold white)
- Font system architecture: display font + body + monospace
- `oklab()` border technique for perceptually smooth edges
- Premium feel for the public-facing surface (sign-up, pricing, about)

---

### [warp.md](./warp.md) — Agent Terminal / Command Output
> "Dark IDE-like interface, block-based command UI"

Warp's warm near-black (earthy, not blue-cold), uppercase spaced category labels, and terminal-block philosophy directly inform how OfficeClaw renders agent command/output streams. The "campfire warmth" prevents the fleet dashboard from feeling sterile. Pill-shaped muted buttons keep the terminal view from feeling like a marketing page.

**Contributes to OfficeClaw:**
- Agent log / terminal output components
- Uppercase letter-spaced section labels (`AGENTS`, `RUNNING`, `QUEUED`)
- Warm tone calibration for dark backgrounds
- Block-based command history styling

---

### [vercel.md](./vercel.md) — Surface Depth / Card System
> "Frontend deployment, black and white precision, Geist font"

Vercel's shadow-as-border technique (`box-shadow: 0 0 0 1px rgba(0,0,0,0.08)`) is the cleanest approach for OfficeClaw's card surfaces — it avoids harsh border lines while maintaining clear separation. Multi-layer shadow stacks (border + elevation + ambient in one declaration) create the depth needed for agent cards, modals, and sidebars. Workflow accent colors (ship/preview/develop) model agent lifecycle state colors.

**Contributes to OfficeClaw:**
- Agent card surface and depth system
- Shadow-as-border technique (no hard `border:` lines on cards)
- Agent lifecycle state colors (created → running → stopped → errored)
- Geist Mono as a candidate monospace companion

---

### [raycast.md](./raycast.md) — Agent Launcher / Command Palette
> "Sleek dark chrome, vibrant gradient accents"

Raycast is a keyboard-first launcher — structurally identical to how users will invoke agents in OfficeClaw. The macOS-native layered shadow with inset highlights creates physical depth on the command modal. Positive letter-spacing on body text (0.2px) counterintuitively makes dark-mode text feel less dense and more readable at command-entry scale.

**Contributes to OfficeClaw:**
- Agent quick-launch / command palette component
- Modal depth via macOS-native multi-layer shadow + inset highlight
- Keyboard shortcut display styling (gradient key caps)
- Letter-spacing strategy for searchable/selectable dark-mode text

---

### [supabase.md](./supabase.md) — Token Architecture / Open-Source Dev Platform
> "Dark emerald theme, code-first"

Supabase shares OfficeClaw's tech stack DNA (Postgres, open-source, developer-first) and runs a similar emerald green accent. Their HSL-based token system with alpha channels (`--colors-slateA12`) is the most sophisticated approach for managing dark-mode color depth through translucency. Pill vs. 6px radius contrast for CTA hierarchy applies directly.

**Contributes to OfficeClaw:**
- HSL + alpha token system for dark-mode layering
- CTA hierarchy: pill for primary ("Launch Agent"), 6px for secondary
- Emerald green validation against similar brand positioning
- Translucent surface layering via `rgba` and `hsla` tokens

---

## How These References Combine into OfficeClaw's Theme

| Concern | Primary Ref | Supporting |
|---|---|---|
| Canvas & dark atmosphere | VoltAgent | Linear, Warp |
| Accent color system | VoltAgent | Supabase |
| Agent-type color tokens | HashiCorp | Vercel (lifecycle states) |
| Typography system | Cursor (display+body+mono) | Linear (density), Warp (warmth) |
| Agent lists & data density | Linear | HashiCorp |
| Agent cards & surfaces | Vercel | Supabase |
| Terminal / command output | Warp | VoltAgent |
| Command palette / launcher | Raycast | Linear |
| Token architecture | Supabase | HashiCorp |
| Marketing / landing page | Cursor | — |

**The resulting identity:** Dark, terminal-native, warm-toned (not cold blue-black), single emerald accent for active/running state, dense precision for fleet data, elevated depth for agent cards, and a warm-cream light mode for the public landing surface.
