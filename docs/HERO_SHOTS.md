# Hero Shots

Three screens carry the entire demo. Every other Helios screen is supporting cast. These three are what judges will remember on the way home, what gets screenshotted in write-ups, and what determines the visual score on the rubric.

This doc tells Sayan exactly where to over-invest pixel polish and where it's safe to stay generic.

---

## Why this doc exists

Demos with 30 mediocre screens lose to demos with 3 excellent screens. Bobcoin budget is finite. Visual polish is the single highest-variance factor in how judges perceive maturity. We pick three frames, ship them at production-grade fidelity, and let everything else be functional.

The three were selected because each one **summarises a feature in a single still image** — meaning a judge can recall the product without rewatching the demo. That's what gets quoted in deliberations.

---

## Hero Shot 1 — Region Atlas diff view

**What it shows:** two-column Monaco editor, `int2.yaml` on the left, `int3.yaml` on the right, with seven highlighted differences and reasoning popovers.

**Why it's a hero shot:** the moment any z-shop dev sees this, they think "finally." It's the most photogenic still in the entire app and the line in the README that draws non-Z judges in.

**On screen for:** ~8 seconds in the demo, scene 1, beat 2.

### Visual spec

| Property | Value |
|---|---|
| Layout | 50/50 split, full viewport width 1440px |
| Editor font | JetBrains Mono 14px, 1.5 line height |
| Theme | Helios dark (background `#0d1117`, panel `#161b22`, accent `#58a6ff`) |
| Diff highlight | Soft amber `rgba(255, 191, 71, 0.25)` background on changed lines |
| Connector lines | 1px `#58a6ff` SVG arcs between left and right matching keys, opacity 0.4 |
| Reasoning popover | Triggered on hover of any highlighted diff. Card width 320px, soft drop-shadow, 8px radius, contains: rule name (e.g., "DB2 subsystem"), explanation, "from int2 region history" footer link. |
| Header bar | "Region Atlas — int2 → int3" with a chevron to flip direction |
| Footer chip | "7 differences detected • 3 require backup pair" |

### Required interactions during demo

1. Open the file. Both panes load with diff highlights pre-rendered (no spinner allowed).
2. Hover one popover — it appears within 100ms.
3. Click "Promote with these substitutions" button bottom-right.
4. Pane fades to next state (loading → Confidence Score).

### What can be cut if Bobcoins run low

- The connector line arcs (nice-to-have, but the highlights alone read clearly).
- The flip-direction chevron (set fixed direction for demo).

### What absolutely cannot be cut

- The reasoning popover. This is the IP differentiation — it's why this isn't just `git diff`.

### Test before recording

Open it on a 13" laptop screen at 1440x900 native. The right column's text must remain legible. If it's not, font goes to 13px and pane padding shrinks. Demo is recorded on a laptop, not a desktop.

---

## Hero Shot 2 — Confidence Score gauge

**What it shows:** a circular gauge animating from 62 (red zone) → 94 (green zone) → 100 (deep green) over ~4 seconds, with the top three score-affecting reasons scrolling alongside.

**Why it's a hero shot:** this is the one frame that explains the entire product to a non-mainframe judge. It says "Helios gives you one number you can trust." Every enterprise judge instinctively understands this.

**On screen for:** ~6 seconds in the demo, scene 1 climax.

### Visual spec

| Property | Value |
|---|---|
| Gauge size | 280px diameter, centered |
| Gauge style | D3 arc (3/4 circle, sweep from 7 o'clock clockwise to 5 o'clock) |
| Track color | `#21262d` (dark) |
| Fill gradient | red `#f85149` → amber `#f0a020` → green `#3fb950`, smooth interpolation |
| Number | 96px Inter Display, weight 800, white, centered |
| Label below | "CONFIDENCE" 12px tracked +0.2em, opacity 0.6 |
| Reasons panel | Right of gauge, 320px wide, three rows, each: severity dot + rule name + delta in coins (e.g., "−30 backup gap") |
| Animation | spring physics (mass 1, stiffness 80, damping 12), staggered by 200ms when reasons resolve |
| Transitions | 62 holds 1s → animates to 94 over 1.5s as backup is generated → animates to 100 over 1.5s as copybook fix lands |

### Required interactions during demo

1. Score appears at 62, red zone, three reasons stacked: backup gap, copybook drift, region mismatch.
2. Maya clicks "Generate paired backup."
3. Gauge sweeps 62→94, "backup gap" reason fades out with a strikethrough.
4. Maya clicks "Auto-fix copybook drift."
5. Gauge sweeps 94→100, "copybook drift" reason fades out.
6. Last reason ("region mismatch") was already auto-resolved; it fades when score hits 100.
7. Gauge holds at 100 with a subtle pulse animation (scale 1.0 → 1.02 → 1.0 over 2s, infinite).

### What can be cut

- The pulse animation on hold (gauge can sit static at 100).
- The severity dot color variation (use one neutral color).

### What absolutely cannot be cut

- The 62 → 94 → 100 sweep. This is the demo's emotional arc in a single visual. Without it, scene 1 has no climax.

### Test before recording

Record at 60fps minimum. The sweep should look buttery. If it stutters, drop the spring physics for a simpler ease-out cubic. Stutter destroys credibility instantly.

---

## Hero Shot 3 — ABEND Archaeologist three-pane view

**What it shows:** three vertical panels — left: pasted SYSLOG with the `S0C7` line highlighted; middle: COBOL source `CUSTPROC.cbl` with line 247 `WS-CUST-AGE` field highlighted in amber; right: business-rule explanation card from Granite Code with a "Last seen 2024-03-12 in int1 — see runbook" cross-reference.

**Why it's a hero shot:** the modernization-theme money shot. This is what "reverse-engineer undocumented code" looks like as a still image. The screenshot tells the whole story: dump on the left, source in the middle, business rule on the right.

**On screen for:** ~6 seconds in the demo, scene 2 climax.

### Visual spec

| Property | Value |
|---|---|
| Layout | 33/33/33 vertical split, full viewport height |
| Left pane | SYSLOG, monospace, dark background `#0d1117`. Line `IGZ0035S` highlighted with amber left border (4px) and `rgba(255, 191, 71, 0.15)` background. |
| Middle pane | Monaco with COBOL syntax. Line 247 has the same amber treatment. Field `WS-CUST-AGE` has a subtle pulsing dot to its left (CSS animation, 2s loop). |
| Right pane | Card stack on slightly lighter background `#161b22`. Top card: "ABEND code: S0C7 — Data exception" with a red severity chip. Middle card: "Business rule" with two paragraphs of Granite-generated text and a "Source: paragraph 2300-CALC-RETIREMENT" footer. Bottom card: "Last seen" with the runbook cross-reference link styled as a button. |
| Right pane font | Inter 15px body, 1.6 line height, comfortable for screenshot reading. |
| Connecting visual | A thin amber line (1px, 50% opacity) drawn from the highlighted SYSLOG line through the highlighted COBOL line into the explanation card. This is the visual signature of "we traced it." |

### Required interactions during demo

1. Maya pastes the SYSLOG into the left pane.
2. The `S0C7` line lights up after a ~400ms "thinking" delay (avoid making it instant; the delay reads as analysis).
3. The middle pane scrolls to line 247 with a smooth animation.
4. The right pane resolves card-by-card with a 300ms stagger.
5. The connecting line draws from left to middle to right over 800ms.

### What can be cut

- The connecting line (high effort, marginal value if other elements land).
- The pulsing dot on `WS-CUST-AGE` (the highlight is enough).

### What absolutely cannot be cut

- The cross-reference to the prior incident's runbook. This is the learning loop in visible form — it's why Helios isn't just an LLM with a UI.

### Test before recording

Read the right pane at recording resolution. If a non-mainframe person can't grasp what happened in 6 seconds of looking at this frame alone, the explanation copy needs to be tightened. Test with a non-Z friend before locking in the text.

---

## Production checklist for all three

Before the demo recording session:

- [ ] Each hero shot renders without dev-tools errors
- [ ] Each hero shot is keyboard-navigable so Maya's "click" actions can be hit reliably even if the trackpad lags
- [ ] Each animation has been recorded once at 60fps and reviewed frame-by-frame for stutter
- [ ] Color contrast passes WCAG AA in dark mode (the `axe` browser extension takes 30 seconds to verify)
- [ ] Loading states exist for the case where the API is slow on demo day — never let a hero shot show a blank panel
- [ ] Each hero shot has a "frozen" mode that disables animations, for use if we end up doing live screenshots
- [ ] Each hero shot has been opened in Chrome and Safari (judges may use either when reviewing the recording)

---

## Bobcoin budget specifically for hero shots

From `BOBCOIN_BUDGET.md`, Sayan's allocation:

| Hero shot | Sayan's coins |
|---|---|
| Region Atlas diff view | 5 |
| Confidence Score gauge | 6 |
| ABEND three-pane view | 5 |
| **Total** | **16 of 40** |

That's 40% of Sayan's entire Bobcoin budget on three screens. That's correct. These are the screens that decide our score.

If a hero shot starts running over budget:
1. First, switch to Plan mode and re-spec what's actually needed.
2. Second, cut from the "what can be cut" lists above.
3. Third, escalate to Golden — he can take over backend integration of the screen so Sayan stays focused on visuals.
4. Last resort: use Claude Code on Golden's machine to scaffold the layout, then hand back to Sayan in Bob for polish. The Bob session report still shows meaningful Sayan work on the visual layer.

---

## What's NOT a hero shot

These features get functional UI but do **not** get hero-shot polish:

- The audit log viewer (table, sortable, no animation)
- The Review Queue (toast notifications + standard list)
- The region YAML editor (Monaco with default theme)
- The JJSCAN+ raw findings panel (table view)
- The runbook browser (markdown render, plain)
- All settings screens

If Sayan is unsure whether a screen warrants polish: if it's not in this doc, it doesn't.
