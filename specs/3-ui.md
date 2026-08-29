---
id: UI
title: UI
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 3 — UI

Companion to [`2-architecture.md`](2-architecture.md), which says where frontend files live. This
document says **what they look like**. Behaviour — what happens, in what order — is
[`4-ux.md`](4-ux.md).

Where a value and a behaviour describe the same thing, this file owns the value and `4-ux.md` owns
the behaviour.

## 1. Direction

The reference is the visual system of auditstage.com, analysed from its live DOM rather than
described from memory. What makes that site work is not its colour: it is **restraint**. Two
typefaces, one accent, four radius values, one transition duration, and no gradients in the
interface.

We take the system and invert the surface.

**UI-001. Why not the dark theme.** That site is a B2B marketing page. This is a consumer financial
interface: twelve form fields, a document checklist, and numbers that have to be read carefully, on a
phone, in daylight. Dark surfaces cost legibility here and buy nothing. Oper's own product is light.

**UI-002. The layout decision:** light application surface, one near-black header band. The dark band
gives the page an anchor and a nod to the reference without adopting its identity.

### 1.1 Taken from the reference

| ID | Property | Value | Why |
|---|---|---|---|
| UI-003 | Body text weight | **500, not 400** | The single cheapest change with the largest effect. It is what makes their interface look dense and deliberate. |
| UI-004 | Negative tracking on headings | −0.03em from 28px up | Large type set at default tracking reads amateur. |
| UI-005 | Radii | 6px controls, 8px cards, nothing rounder | |
| UI-006 | Transition | **120ms ease** | Slow animation in a financial interface reads as lag. |
| UI-007 | Accent discipline | Exactly one accent colour | Their real design move. |

### 1.2 Not taken

- **UI-008** — Their black-and-yellow identity. We are building for a different company; lifting the
  palette wholesale would be recognisably theirs.
- **UI-009** — The six-layer Framer shadow. It is a template default and looks muddy on light
  surfaces.
- **UI-010** — 70px hero headings and carousels. No marketing page here.

## 2. Colour

**UI-011.** Light surface, near-black ink, one accent, one signal colour used as fill only.

```
--color-ink            #101413    primary text, header band
--color-ink-soft       #2B3230    secondary headings

--color-surface        #FFFFFF    page
--color-surface-2      #F5F7F6    panels, table stripes
--color-surface-3      #EBEFEE    input backgrounds, hover
--color-border         #DDE3E1    hairlines
--color-border-strong  #C3CCC9    focused / emphasised

--color-muted          #6B7472    labels, captions, help text

--color-accent         #0B5D5B    primary actions, links, active states
--color-accent-hover   #084745
--color-accent-soft    #E3EFEE    tinted backgrounds, selected rows

--color-signal         #C8A415    the "cash needed" highlight, progress fills
--color-signal-soft    #FBF3D8

--color-danger         #A8331F
--color-danger-soft    #FAEDEA
--color-success        #1F6B4A
--color-success-soft   #E7F2EC
```

**Contrast rules, non-negotiable:**

- **UI-012** — `--color-signal` is a **fill only**. Never text on white: it measures roughly 2.6:1
  and fails WCAG AA outright. On a signal fill, text is `--color-ink`. This mirrors how the reference
  uses its yellow — always a background with dark text, never a text colour.
- **UI-013** — `--color-accent` on white is roughly 7:1 and is safe for text.
- **UI-014** — `--color-muted` on white is roughly 4.9:1 and is safe for body text but not for
  anything below 12px.

## 3. Typography

**UI-015.** Two families, both on Google Fonts, loaded with `display=swap` and preconnect.

- **Display: Plus Jakarta Sans.** Headings only.
- **Body / UI: Figtree.** Everything else. Default weight 500.

### 3.1 Scale

**UI-016.**

| Role | Family | Size / line-height | Weight | Tracking |
|---|---|---|---|---|
| `display` — the simulator result figure | Jakarta | 44 / 46 | 700 | −0.035em |
| `h1` — page title | Jakarta | 32 / 36 | 600 | −0.03em |
| `h2` — section | Jakarta | 24 / 28 | 600 | −0.02em |
| `h3` — card title | Jakarta | 18 / 24 | 600 | −0.01em |
| `body` | Figtree | 15 / 22 | 500 | 0 |
| `body-sm` — help text | Figtree | 13 / 18 | 500 | 0 |
| `label` — field labels | Figtree | 13 / 16 | 600 | 0 |
| `eyebrow` — section kickers | Figtree | 11 / 14 | 600 | 0.08em, uppercase |
| `mono` — Dutch terms, codes, figures in tables | Fragment Mono | 13 / 18 | 400 | 0 |

**UI-017. Numbers use tabular figures.** `font-variant-numeric: tabular-nums` on every element
showing money, so columns align and a changing figure does not shift the layout.

**UI-018.** Dutch domain terms (`quotiteit`, `eigen inbreng`, `JKP`) render in `mono` at
`--color-accent`. This is the one decorative decision in the whole system, and it does real work: it
marks domain vocabulary as domain vocabulary.

## 4. Spacing, radii, motion

**UI-019.** Spacing is a 4px scale. Use only `1 2 3 4 6 8 12 16` from Tailwind's default scale
(4/8/12/16/24/32/48/64px). Nothing in between.

**UI-020.**

```
--radius-control  6px    buttons, inputs, selects
--radius-card     8px    cards, panels, upload zones
--radius-pill     999px  status chips only

--shadow-card     0 1px 2px rgba(16,20,19,.04), 0 1px 3px rgba(16,20,19,.06)
--shadow-raised   0 4px 12px rgba(16,20,19,.08)

--duration        120ms
--ease            cubic-bezier(.4, 0, .2, 1)
```

**UI-021.** Only two shadow levels exist. Most surfaces use a border instead of a shadow.

**UI-022. Motion budget:** transitions on `background-color`, `border-color`, `color`, `opacity`,
`transform`. Never on `width`, `height` or `box-shadow`. No entrance animations, no scroll reveals,
no skeleton shimmer. A spinner on pending requests is the only loading affordance.

## 5. Tailwind

**UI-023. Tailwind is the styling system. It is not optional and it is not a fallback.**

### 5.1 Setup

**UI-024.** Tailwind v4, CSS-first configuration. There is no `tailwind.config.js`; the theme lives
in `src/styles.css` (see `2-architecture.md` ARC-020 for placement):

```css
@import "tailwindcss";
@plugin "tailwindcss-primeui";

@theme {
  --font-display: "Plus Jakarta Sans", sans-serif;
  --font-sans: "Figtree", sans-serif;
  --font-mono: "Fragment Mono", monospace;

  --color-ink: #101413;
  --color-ink-soft: #2B3230;
  --color-surface: #FFFFFF;
  --color-surface-2: #F5F7F6;
  --color-surface-3: #EBEFEE;
  --color-border: #DDE3E1;
  --color-border-strong: #C3CCC9;
  --color-muted: #6B7472;
  --color-accent: #0B5D5B;
  --color-accent-hover: #084745;
  --color-accent-soft: #E3EFEE;
  --color-signal: #C8A415;
  --color-signal-soft: #FBF3D8;
  --color-danger: #A8331F;
  --color-danger-soft: #FAEDEA;
  --color-success: #1F6B4A;
  --color-success-soft: #E7F2EC;

  --radius-control: 6px;
  --radius-card: 8px;

  --default-transition-duration: 120ms;
}

@layer base {
  body {
    @apply bg-surface text-ink font-sans font-medium antialiased;
  }
  .tabular {
    font-variant-numeric: tabular-nums;
  }
}
```

**UI-025.** That `@layer base` block is the **only** place `@apply` is permitted in the entire
codebase.

### 5.2 Hard rules for anyone, human or agent, writing frontend code

- **UI-026** — **All styling is Tailwind utility classes in the template.** No exceptions below.
- **UI-027** — **Every component stylesheet stays empty** — that is, every `.css` file under `src/`
  except `src/styles.css`. If one has content, the work is not done. `make lint` fails on it
  (`5-deployment.md` DEP-038). (The source said "a CI step"; CI is a deliberate non-goal —
  `1-code-quality.md` §13.)

  Stated as "every `.css` except `styles.css`" rather than "every `*.component.css`", which is how it
  read until T43. Angular 22 generates `app.css` for the root component, so the narrower glob matched
  nothing: the check ran, found no files, and passed while a stylesheet had content. `angular.json`
  additionally configures the schematics to emit `<name>.component.ts` for generated components, so
  new files follow ARC-034 — but the lint rule no longer depends on that holding.
- **UI-028** — **No `@apply` outside the base layer.** `@apply` moves utilities into a stylesheet and
  re-creates the problem Tailwind exists to solve. If a class list repeats, extract an Angular
  component, not a CSS class.
- **UI-029** — **No `[ngStyle]`, no `style="..."`, no inline styles.** Dynamic styling uses `[class]`
  or `[ngClass]` with whole utility strings, never computed CSS values.
- **UI-030** — **Colours come from theme tokens only.** `bg-accent`, `text-muted`, `border-border`.
  Never `bg-[#0B5D5B]`, never `text-teal-700`. If a colour is needed that is not in `@theme`, it is
  added to `@theme` first.

  **There are exactly two token surfaces, and a hex literal is legal in both:** `src/styles.css`
  (the `@theme` block) and `src/app/core/theme/oper-preset.ts` (the PrimeNG palette, UI-039). They
  are the same layer expressed twice because PrimeNG's preset is TypeScript, not CSS — ARC-037 names
  them together for this reason. The `make lint` check excludes the `theme/` directory accordingly;
  an earlier wording forbade hex in every `.ts` file, which would have failed against the preset
  this spec itself mandates.
- **UI-031** — **Spacing comes from the scale.** `p-4`, `gap-6`, `mt-8`. Never `p-[13px]`.
- **UI-032** — **Arbitrary values are forbidden** except for one-off layout constraints that
  genuinely have no token, for example `max-w-[42rem]`. Colours, spacing and radii never qualify.
- **UI-033** — **Class order:** layout → box model → typography → colour → state.
  `flex items-center gap-3 px-4 py-2 text-sm font-semibold text-ink bg-surface-2 rounded-control
  hover:bg-surface-3`. Prettier with `prettier-plugin-tailwindcss` enforces this (`1-code-quality.md`
  CQ-078); do not hand-order.
- **UI-034** — **Responsive is mobile-first.** Base styles are the phone. `md:` and up widen. There
  is no desktop-only layout. Build order and rationale: `4-ux.md` UX-003.

### 5.3 Why this matters here

A mortgage simulator is a form. Forms are where design systems rot: one component gets a custom
stylesheet, then another, and six files later nothing is consistent. Utilities in the template keep
every visual decision visible at the point of use and reviewable in a diff.

## 6. PrimeNG

**UI-035.** PrimeNG in **styled mode** with a custom preset. Not unstyled mode: that path is correct
for a team that already owns a design system, and its setup cost does not fit the time budget.

**UI-036.** Used for exactly four things, because hand-rolling them is tedious and error-prone:

| Component | Used for |
|---|---|
| `p-stepper` | The multi-step application form |
| `p-fileupload` | Document upload, drag and drop, per-type |
| `p-inputnumber` | Currency and percentage fields with locale formatting |
| `p-select` | Region, employment type, property type |

**UI-037.** Everything else — buttons, cards, checklist rows, badges, the results panel — is a plain
Angular component styled with Tailwind. Do not reach for a PrimeNG component when a `<button>` will
do.

### 6.1 Configuration

**UI-038.** Layer order matters, or PrimeNG's styles will beat Tailwind's utilities:

```ts
providePrimeNG({
  theme: {
    preset: OperPreset,
    options: {
      darkModeSelector: false,
      cssLayer: { name: 'primeng', order: 'theme, base, primeng, components, utilities' },
    },
  },
})
```

### 6.2 The preset

**UI-039.** One file, `src/app/core/theme/oper-preset.ts`. The entire visual language of the PrimeNG
components lives here. **Component styles are never overridden with CSS classes** — if something
looks wrong, the token is wrong. Structural rule: `2-architecture.md` ARC-037.

```ts
import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

export const OperPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#E3EFEE', 100: '#C7DFDD', 200: '#9BC5C2', 300: '#6FABA7',
      400: '#43918C', 500: '#0B5D5B', 600: '#084745', 700: '#063A38',
      800: '#052D2C', 900: '#032120', 950: '#021413',
    },
    formField: {
      paddingX: '0.75rem',
      paddingY: '0.625rem',
      borderRadius: '6px',
      focusRing: { width: '2px', style: 'solid', color: '{primary.500}', offset: '1px' },
    },
    content: { borderRadius: '8px' },
    transitionDuration: '120ms',
  },
});
```

**UI-040.** Money fields use `mode="currency" currency="EUR" locale="nl-BE"`, which produces the
Belgian formatting a local reviewer expects. Money crosses the wire as a string, never a number:
`1-code-quality.md` CQ-014, `2-architecture.md` ARC-026.

## 7. Components

### 7.1 Buttons

**UI-041.** Three variants only. Height 40px, radius 6px, `text-sm font-semibold`, 120ms transition.

| Variant | Classes |
|---|---|
| Primary | `bg-accent text-white hover:bg-accent-hover` |
| Secondary | `bg-surface-2 text-ink border border-border hover:bg-surface-3` |
| Ghost | `text-accent hover:bg-accent-soft` |

**UI-042.** Focus is always visible: `focus-visible:outline-2 focus-visible:outline-offset-2
focus-visible:outline-accent`. Disabled is `opacity-50 cursor-not-allowed`, never a colour change.

### 7.2 Inputs

**UI-043.** `bg-surface-3 border border-border rounded-control px-3 py-2.5 text-base`.

**UI-044.** Base font-size stays at 16px on mobile — anything smaller triggers iOS zoom on focus.

**UI-045.** Label above the field, `label` scale. Help text below in `body-sm text-muted`.

**UI-046.** Error state: `border-danger` plus the message in `text-danger text-sm`. When the message
appears and where it comes from is behaviour: `4-ux.md` UX-018 – UX-021.

### 7.3 The result panel

The one place the design raises its voice, because it holds the two numbers the borrower came for.

- **UI-047** — Monthly payment: `display` scale, `text-ink`, tabular figures.
- **UI-048** — **Total cash needed: same scale, on a `bg-signal-soft` panel with a `border-l-4
  border-signal` left rule.** This is where the signal colour earns its place, and it is the number
  that surprises people.
- **UI-049** — Everything else — total repaid, total interest, JKP, quotiteit — in a plain definition
  list, `body-sm`, labels in `text-muted`.
- **UI-050** — `quotiteit` above 90% shows a chip: `bg-signal-soft text-ink rounded-pill px-2 py-0.5
  text-xs font-semibold`. It is informational, not an error, and must not be styled as one.
  → `0-business-logic.md` DOM-016, ERR-006.

### 7.4 Cost breakdown

**UI-051.** A borderless table, `text-sm`, rows separated by `border-b border-border`, amounts
right-aligned with tabular figures, Dutch term in `mono text-accent` and the plain-language name
beneath in `text-muted text-xs`. Total row: `border-t-2 border-ink font-semibold`, no bottom border.

### 7.5 Checklist row

**UI-052.** Grid: status icon, label block, action. Satisfied rows carry `bg-success-soft` with a
check; outstanding rows stay on `bg-surface` with an upload control. Required and not satisfied gets
`text-ink`; optional gets `text-muted`.

### 7.6 Status chips

**UI-053.** `rounded-pill px-2.5 py-1 text-xs font-semibold`. Draft `bg-surface-3 text-muted`,
pending `bg-signal-soft text-ink`, complete `bg-success-soft text-success`, withdrawn `bg-danger-soft
text-danger`.

## 8. Screens

**UI-054.**

| Screen | Layout | Components |
|---|---|---|
| Simulator | Two columns on `md:` and up: form left, sticky result right. Stacked on mobile. | `p-inputnumber`, `p-select`, result panel, cost table |
| Sign up | Single centred card, `max-w-[24rem]` | Plain inputs, primary button |
| Application wizard | `p-stepper`, one step per panel, `max-w-[42rem]` | Stepper, inputs, selects |
| Documents | Checklist, one row per requirement | `p-fileupload` per row, status chips |
| Application detail | Header with status chip, checklist below | Chips, checklist rows |

**UI-055.** Header: near-black band, `bg-ink`, 56px tall, product name on the left in `display` at
18px, account menu on the right. It is the only dark surface in the application.

**UI-056.** Page width caps at `max-w-[72rem]` with `px-4 md:px-8`.

## 9. Accessibility floor

Not negotiable, and cheap:

- **UI-057** — Visible focus ring on every interactive element. Never `outline: none` without a
  replacement.
- **UI-058** — Every input has a `<label for>`. Placeholder is not a label.
- **UI-059** — Colour never carries meaning alone: a status chip has text, an error has a message.
- **UI-060** — Contrast: 4.5:1 for body text, 3:1 for large text and for UI borders.
- **UI-061** — `prefers-reduced-motion` disables all transitions.
- **UI-062** — The whole flow is keyboard-navigable, including file upload.

## 10. Definition of done

- **UI-063** — Every `*.component.css` is empty.
- **UI-064** — No hex value appears outside the two token surfaces named in UI-030.
- **UI-065** — No `@apply` outside `@layer base`.
- **UI-066** — The result panel shows the cash-needed figure on the signal surface.
- **UI-067** — Focus is visible on every control, and the flow completes with the keyboard alone.

---

# Appendix A — Traceability

Source: `05-ui.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| UI-001 | Light surface, not the reference's dark theme | Direction | §1 |
| UI-002 | Light application surface, one near-black header band | Direction | §1 |
| UI-003 | Body text weight 500, not 400 | Taken from the reference | §1.1 |
| UI-004 | Negative tracking −0.03em from 28px up | Taken from the reference | §1.1 |
| UI-005 | Radii 6px controls, 8px cards, nothing rounder | Taken from the reference | §1.1 |
| UI-006 | 120ms ease transition | Taken from the reference | §1.1 |
| UI-007 | Exactly one accent colour | Taken from the reference | §1.1 |
| UI-008 | Not taken: the black-and-yellow identity | Not taken | §1.2 |
| UI-009 | Not taken: the six-layer Framer shadow | Not taken | §1.2 |
| UI-010 | Not taken: 70px hero headings and carousels | Not taken | §1.2 |
| UI-011 | The colour tokens | 1 Colour | §2 |
| UI-012 | `--color-signal` is a fill only, never text | 1 Colour | §2 |
| UI-013 | `--color-accent` on white is safe for text | 1 Colour | §2 |
| UI-014 | `--color-muted` is safe for body text, not below 12px | 1 Colour | §2 |
| UI-015 | Two families: Plus Jakarta Sans and Figtree | 2 Typography | §3 |
| UI-016 | The type scale | 2 Typography | §3.1 |
| UI-017 | Tabular figures on every money element | 2 Typography | §3.1 |
| UI-018 | Dutch domain terms in `mono` at `--color-accent` | 2 Typography | §3.1 |
| UI-019 | 4px spacing scale, nothing in between | 3 Spacing, radii, motion | §4 |
| UI-020 | Radii, shadows, duration, easing tokens | 3 Spacing, radii, motion | §4 |
| UI-021 | Only two shadow levels; prefer a border | 3 Spacing, radii, motion | §4 |
| UI-022 | Motion budget | 3 Spacing, radii, motion | §4 |
| UI-023 | Tailwind is the styling system, not a fallback | 4 Tailwind | §5 |
| UI-024 | Tailwind v4, CSS-first, theme in `src/styles.css` | 4 Setup | §5.1 |
| UI-025 | `@layer base` is the only place `@apply` is permitted | 4 Setup | §5.1 |
| UI-026 | All styling is utility classes in the template | 4 Hard rules, 1 | §5.2 |
| UI-027 | Every `*.component.css` stays empty | 4 Hard rules, 2 | §5.2 |
| UI-028 | No `@apply` outside the base layer | 4 Hard rules, 3 | §5.2 |
| UI-029 | No `[ngStyle]`, no `style="..."`, no inline styles | 4 Hard rules, 4 | §5.2 |
| UI-030 | Colours come from theme tokens only | 4 Hard rules, 5 | §5.2 |
| UI-031 | Spacing comes from the scale | 4 Hard rules, 6 | §5.2 |
| UI-032 | Arbitrary values forbidden except one-off layout | 4 Hard rules, 7 | §5.2 |
| UI-033 | Class order, enforced by Prettier | 4 Hard rules, 8 | §5.2 |
| UI-034 | Responsive is mobile-first | 4 Hard rules, 9 | §5.2 |
| UI-035 | PrimeNG in styled mode with a custom preset | 5 PrimeNG | §6 |
| UI-036 | Exactly four PrimeNG components | 5 PrimeNG | §6 |
| UI-037 | Everything else is plain Angular plus Tailwind | 5 PrimeNG | §6 |
| UI-038 | CSS layer order, or PrimeNG beats Tailwind | 5 Configuration | §6.1 |
| UI-039 | The preset is one file and the only styling surface | 5 The preset | §6.2 |
| UI-040 | Money fields use EUR / nl-BE formatting | 5 The preset | §6.2 |
| UI-041 | Three button variants, 40px, radius 6px | 6 Buttons | §7.1 |
| UI-042 | Focus always visible; disabled is opacity only | 6 Buttons | §7.1 |
| UI-043 | Input base classes | 6 Inputs | §7.2 |
| UI-044 | Input font-size stays 16px against iOS zoom | 6 Inputs | §7.2 |
| UI-045 | Label above, help text below | 6 Inputs | §7.2 |
| UI-046 | Error state styling | 6 Inputs | §7.2 |
| UI-047 | Monthly payment at `display` scale | 6 The result panel | §7.3 |
| UI-048 | Cash needed on the signal surface with a left rule | 6 The result panel | §7.3 |
| UI-049 | Secondary figures in a plain definition list | 6 The result panel | §7.3 |
| UI-050 | Quotiteit chip above 90%, informational | 6 The result panel | §7.3 |
| UI-051 | Cost breakdown table | 6 Cost breakdown | §7.4 |
| UI-052 | Checklist row grid and states | 6 Checklist row | §7.5 |
| UI-053 | Status chip styling per status | 6 Status chips | §7.6 |
| UI-054 | The five screens and their layouts | 7 Screens | §8 |
| UI-055 | Header band, the only dark surface | 7 Screens | §8 |
| UI-056 | Page width caps at `max-w-[72rem]` | 7 Screens | §8 |
| UI-057 | Visible focus ring on every interactive element | 8 Accessibility floor | §9 |
| UI-058 | Every input has a `<label for>` | 8 Accessibility floor | §9 |
| UI-059 | Colour never carries meaning alone | 8 Accessibility floor | §9 |
| UI-060 | Contrast 4.5:1 body, 3:1 large text and borders | 8 Accessibility floor | §9 |
| UI-061 | `prefers-reduced-motion` disables all transitions | 8 Accessibility floor | §9 |
| UI-062 | The whole flow is keyboard-navigable | 8 Accessibility floor | §9 |
| UI-063 | Done: every `*.component.css` is empty | 9 Definition of done | §10 |
| UI-064 | Done: no hex outside `@theme` | 9 Definition of done | §10 |
| UI-065 | Done: no `@apply` outside `@layer base` | 9 Definition of done | §10 |
| UI-066 | Done: cash needed sits on the signal surface | 9 Definition of done | §10 |
| UI-067 | Done: focus visible, flow completes by keyboard | 9 Definition of done | §10 |

# Appendix B — Where the overlaps with `4-ux.md` live

Six statements appear in both source documents. **This file owns the value; `4-ux.md` owns the
behaviour.** Two go the other way, marked below, because they are sequencing and behaviour rather
than measurements.

| Statement | Canonical | The other file |
|---|---|---|
| Input base font-size 16px, iOS zoom | **UI-044** | UX states touch targets and no-zoom-on-focus, points here |
| `max-w-[72rem]`, `px-4 md:px-8` | **UI-056** | UX states single column everywhere, points here |
| Two-column simulator at `md:` | **UI-054** | UX states exactly one two-column layout, points here |
| Motion budget, no entrance animation | **UI-022** | UX "Not doing" points here |
| Mobile-first as a build order | `4-ux.md` **UX-003** | UI-034 states the rule, points there |
| Error beside the field, text from a backend code | `4-ux.md` **UX-018 – UX-021** | UI-046 keeps the visual treatment only |

## Enforcement

`ruff` and `mypy` are irrelevant here. Of the rules above, only these are machine-checkable, and the
gate for all of them is `make lint` — CI is a deliberate non-goal (`1-code-quality.md` §13). The
last two rows are shell checks written directly into the `lint` target (`5-deployment.md` DEP-038);
the first three arrive with the frontend toolchain at `10-implementation.md` T26:

| Would be enforced by | Rules |
|---|---|
| `prettier-plugin-tailwindcss` | UI-033 class order |
| ESLint (`@angular-eslint`) | UI-029 inline styles |
| A `make lint` step asserting every `*.component.css` is empty | UI-027, UI-063 |
| `make lint` greps for a hex outside `src/styles.css` and `core/theme/` | UI-030, UI-064 |
| `grep` for `@apply` outside `@layer base` | UI-028, UI-065 |
| **Playwright** (batch 4) | UI-067 focus visible and the flow completes by keyboard; UI-063 and UI-066 asserted in a real browser |
| **review** | everything else — the tokens, the scale, the component recipes, the accessibility floor |

**UI-068. Playwright is a gate, not a convenience.** The rules above that "review" covers are the
ones a human checks at a 375px window and stops checking once the window is closed. A handful of
browser scenarios turn `UI-066`, `UI-067`, `UX-055`, `UX-056` and `UX-061` into something that fails
a build instead of a memory. Installed and written in T26 – T30; the scenarios are named there.
