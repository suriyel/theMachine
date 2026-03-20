# Code Context Retrieval MCP System — UCD Style Guide

**Date**: 2026-03-21
**Status**: Approved
**SRS Reference**: docs/plans/2026-03-21-code-context-retrieval-srs.md
**Visual Direction**: Developer Dark (GitHub Dark + Sourcegraph reference)

---

## 1. Visual Style Direction

**Chosen Style**: Developer Dark

**Mood**: A focused, low-distraction dark interface optimized for reading code. High-contrast syntax highlighting against a near-black background. Dense information layout that respects developers' preference for efficiency over decoration.

**Rationale**: The primary UI persona (Software Developer, intermediate to expert) spends extended time reading code. Dark themes reduce eye strain during long sessions and provide superior contrast for syntax highlighting. This aligns with the reference systems (GitHub Code Search, Sourcegraph) that the target users are already familiar with.

---

## 2. Style Tokens

### 2.1 Color Palette

| Token | Hex | Usage | Contrast Ratio |
|-------|-----|-------|----------------|
| `--color-primary` | `#58a6ff` | Primary actions, links, active states, search button | 5.2:1 on `--color-bg-primary` |
| `--color-primary-hover` | `#79c0ff` | Hover state for primary elements | 6.8:1 on `--color-bg-primary` |
| `--color-secondary` | `#8b949e` | Secondary text, inactive tabs, metadata | 4.6:1 on `--color-bg-primary` |
| `--color-bg-primary` | `#0d1117` | Main page background | — |
| `--color-bg-secondary` | `#161b22` | Card backgrounds, code blocks, input fields | — |
| `--color-bg-tertiary` | `#21262d` | Hover backgrounds, selected states | — |
| `--color-text-primary` | `#e6edf3` | Body text, headings | 13.5:1 on `--color-bg-primary` |
| `--color-text-secondary` | `#8b949e` | Captions, file paths, timestamps | 4.6:1 on `--color-bg-primary` |
| `--color-text-muted` | `#484f58` | Disabled text, placeholders | 3.1:1 on `--color-bg-primary` |
| `--color-success` | `#3fb950` | Success states, indexed status | 5.5:1 on `--color-bg-primary` |
| `--color-warning` | `#d29922` | Warning states, partial results | 4.8:1 on `--color-bg-primary` |
| `--color-error` | `#f85149` | Error states, failed status | 5.1:1 on `--color-bg-primary` |
| `--color-border` | `#30363d` | Default borders, dividers | — |
| `--color-border-focus` | `#58a6ff` | Focused input borders | — |
| `--color-score-high` | `#58a6ff` | Relevance score >= 0.8 | — |
| `--color-score-medium` | `#d29922` | Relevance score 0.5–0.8 | — |
| `--color-score-low` | `#8b949e` | Relevance score < 0.5 | — |

#### Syntax Highlighting (Monokai-inspired)

| Token | Hex | Usage |
|-------|-----|-------|
| `--syntax-keyword` | `#ff7b72` | Language keywords (if, class, return) |
| `--syntax-string` | `#a5d6ff` | String literals |
| `--syntax-comment` | `#8b949e` | Comments |
| `--syntax-function` | `#d2a8ff` | Function/method names |
| `--syntax-type` | `#79c0ff` | Type names, class names |
| `--syntax-number` | `#79c0ff` | Numeric literals |
| `--syntax-variable` | `#ffa657` | Variables, parameters |
| `--syntax-operator` | `#ff7b72` | Operators |

### 2.2 Typography Scale

| Token | Font Family | Size | Weight | Line Height | Usage |
|-------|-------------|------|--------|-------------|-------|
| `--font-heading-1` | Inter | 24px | 600 | 1.3 | Page title ("Code Context Search") |
| `--font-heading-2` | Inter | 18px | 600 | 1.4 | Section headings |
| `--font-heading-3` | Inter | 14px | 600 | 1.4 | Result card titles (file path) |
| `--font-body` | Inter | 14px | 400 | 1.5 | Body text, descriptions |
| `--font-body-small` | Inter | 12px | 400 | 1.5 | Captions, metadata, scores |
| `--font-label` | Inter | 13px | 500 | 1.4 | Form labels, button text, filter labels |
| `--font-code` | JetBrains Mono | 13px | 400 | 1.6 | Code snippets in results |
| `--font-code-small` | JetBrains Mono | 12px | 400 | 1.5 | Line numbers, symbol badges |

### 2.3 Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight gaps (badge padding, inline spacing) |
| `--space-sm` | 8px | Inner padding (inputs, buttons), gap between tags |
| `--space-md` | 16px | Card padding, section gaps |
| `--space-lg` | 24px | Between result cards, major sections |
| `--space-xl` | 40px | Page top/bottom margins |
| `--radius-sm` | 4px | Buttons, inputs, badges |
| `--radius-md` | 6px | Cards, dropdowns |
| `--radius-lg` | 8px | Modals (if any) |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | Subtle elevation (dropdowns) |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | Cards on hover |
| `--max-width-content` | 960px | Main content column max width |
| `--max-width-page` | 1200px | Full page max width |

### 2.4 Iconography & Imagery

- **Icon style**: Outlined, rounded corners, 1.5px stroke weight
- **Icon library**: Lucide Icons (latest stable)
- **Icon size**: 16px inline with text, 20px in buttons, 24px in empty states
- **Icon color**: Inherits `--color-text-secondary` by default; `--color-primary` for active/interactive
- **No illustrations or photography** — this is a developer tool; icons and text only

---

## 3. Component Prompts

### 3.1 Component: Search Input

**SRS Trace**: FR-017
**Variants**: default, focused, filled, loading

#### Base Prompt
> A wide search input field spanning the full content width (960px max), height 44px, with `--color-bg-secondary` (#161b22) background, 1px solid `--color-border` (#30363d) border, `--radius-sm` (4px) border-radius. Left-aligned 16px Lucide `Search` icon in `--color-text-muted` (#484f58). Placeholder text "Search code context..." in `--font-body` (Inter 14px 400) using `--color-text-muted`. `--space-sm` (8px) padding on all sides, 12px padding-left after the icon. A "Search" button attached to the right end of the input, 44px height, `--color-primary` (#58a6ff) background, white text in `--font-label` (Inter 13px 500), `--radius-sm` corners on the right side only.

#### Variant Prompts
> **Focused**: Border changes to `--color-border-focus` (#58a6ff), subtle glow `0 0 0 3px rgba(88,166,255,0.15)`. Placeholder fades. Search icon stays muted.
> **Filled**: Input text in `--color-text-primary` (#e6edf3) using `--font-body`. Clear button (Lucide `X`, 16px) appears at right of text, before search button.
> **Loading**: Search button text replaced with a 16px spinning loader icon in white. Input disabled with `opacity: 0.7`.

#### Style Constraints
- Input height is exactly 44px for consistent alignment with filters
- Search triggers on Enter key or button click
- Max query length displayed as subtle counter (e.g., "42/500") at right edge when focused

---

### 3.2 Component: Repository Filter Dropdown

**SRS Trace**: FR-017, FR-013
**Variants**: default, open, selected, loading

#### Base Prompt
> A dropdown select, 200px width, 36px height. `--color-bg-secondary` background, 1px `--color-border` border, `--radius-sm` corners. Label "Repository" in `--font-label` (Inter 13px 500) `--color-text-secondary` positioned above. Default text "All repositories" in `--font-body` (Inter 14px) `--color-text-secondary`. Lucide `ChevronDown` icon (16px) at right, `--color-text-muted`. Positioned inline-left below the search input with `--space-sm` gap.

#### Variant Prompts
> **Open**: Dropdown panel drops below, `--color-bg-secondary` background, 1px `--color-border` border, `--shadow-sm`, `--radius-md` corners. List items are 36px height, `--font-body`, hover shows `--color-bg-tertiary` background. Scrollable if > 8 items.
> **Selected**: Selected repo name in `--color-text-primary`. Small `X` button (12px) to clear selection.

---

### 3.3 Component: Language Filter Checkboxes

**SRS Trace**: FR-017, FR-018
**Variants**: default, checked, indeterminate

#### Base Prompt
> A horizontal row of checkbox-label pairs for each supported language: Java, Python, TypeScript, JavaScript, C, C++. Each checkbox is 16px square, `--color-bg-secondary` background, 1px `--color-border` border, `--radius-sm` (4px) corners. Label in `--font-label` (Inter 13px 500) `--color-text-secondary`, 6px gap from checkbox. Checkboxes spaced `--space-md` (16px) apart. Label "Languages" in `--font-label` `--color-text-secondary` above the row. Positioned inline-right of the repository dropdown, same vertical line.

#### Variant Prompts
> **Checked**: Checkbox fills with `--color-primary` (#58a6ff), white checkmark icon (Lucide `Check`, 12px). Label becomes `--color-text-primary`.
> **Indeterminate**: Not applicable — all checkboxes are independent.

---

### 3.4 Component: Result Card

**SRS Trace**: FR-017, FR-010
**Variants**: default, hover, expanded

#### Base Prompt
> A full-width result card (max 960px). `--color-bg-secondary` (#161b22) background, 1px `--color-border` (#30363d) border, `--radius-md` (6px) corners. `--space-md` (16px) padding.
>
> **Header row** (single line): File path in `--font-heading-3` (Inter 14px 600) `--color-primary` (#58a6ff) as a link. Repo name badge to the right — small rounded pill (`--radius-sm`), `--color-bg-tertiary` background, `--font-code-small` (JetBrains Mono 12px) `--color-text-secondary`. Language badge next — same pill style with language name. Relevance score at far right: `--font-body-small` (Inter 12px), color based on score value (`--color-score-high/medium/low`), formatted as percentage (e.g., "93%").
>
> **Symbol line** (below header, if symbol is not null): "symbol:" label in `--font-body-small` `--color-text-muted`, symbol name in `--font-code` (JetBrains Mono 13px) `--color-syntax-function` (#d2a8ff). Omit this line if symbol is null.
>
> **Code block** (main content area): Below symbol line, `--space-sm` gap. Background `--color-bg-primary` (#0d1117), 1px `--color-border` border, `--radius-sm` corners, `--space-sm` (8px) padding. Code content in `--font-code` (JetBrains Mono 13px) with syntax highlighting using the Monokai tokens. Line numbers in `--color-text-muted` at left edge, 40px gutter. Max height 200px with vertical scroll if exceeded. Horizontal scroll for long lines.

#### Variant Prompts
> **Hover**: Card border changes to `--color-border-focus` (#58a6ff), `--shadow-md` applied. Subtle transition (150ms).
> **Expanded**: Max height removed — full code content visible. Toggle via "Show all" / "Collapse" link below the code block in `--font-body-small` `--color-primary`.

#### Style Constraints
- Cards are separated by `--space-lg` (24px) vertical gap
- Maximum 3 result cards per query (Top-3)
- Truncation indicator "..." appears at line 200 if content was truncated by FR-010

---

### 3.5 Component: Empty State

**SRS Trace**: FR-017
**Variants**: no-results, initial

#### Base Prompt
> Centered in the results area, vertically and horizontally. Lucide `SearchX` icon (48px) in `--color-text-muted` (#484f58). Below: message text in `--font-body` (Inter 14px) `--color-text-secondary`. `--space-md` gap between icon and text.

#### Variant Prompts
> **Initial** (before first search): Icon = Lucide `Search` (48px). Text = "Search for code context across indexed repositories". Subtitle in `--font-body-small`: "Try: how to use spring WebClient timeout".
> **No results**: Icon = Lucide `SearchX`. Text = "No results found". Subtitle: "Try a different query or remove filters".

---

### 3.6 Component: Header / Navbar

**SRS Trace**: FR-017
**Variants**: default only

#### Base Prompt
> Full-width header bar, 56px height, `--color-bg-secondary` (#161b22) background, 1px `--color-border` bottom border. Left side: application logo/name "CodeContext" in `--font-heading-2` (Inter 18px 600) `--color-text-primary`, preceded by a Lucide `Code2` icon (20px) in `--color-primary`. Right side: no user menu needed (API key auth, not session-based). Centered within `--max-width-page` (1200px). Fixed at top of viewport.

---

### 3.7 Component: Loading Skeleton

**SRS Trace**: FR-017 (implicit)
**Variants**: default

#### Base Prompt
> While search results are loading, display 3 skeleton result cards matching the Result Card dimensions. Each skeleton card: `--color-bg-secondary` background, `--radius-md` corners. Inside: 3 animated shimmer bars — header bar (60% width, 14px height), symbol bar (30% width, 12px height), code block (100% width, 120px height). Shimmer animation: left-to-right gradient sweep, `--color-bg-tertiary` to `--color-bg-secondary`, 1.5s loop. Cards separated by `--space-lg`.

---

## 4. Page Prompts

### 4.1 Page: Search Page (Main & Only Page)

**SRS Trace**: FR-017, FR-018, FR-013, FR-011, FR-012
**User Persona**: Software Developer
**Entry Points**: Direct URL access, bookmarked page

#### Layout Description
Single-column layout, centered within `--max-width-page` (1200px). Fixed header at top. Content area below header with `--space-xl` (40px) top margin. Search input spans full content width (`--max-width-content` 960px), centered. Filters row directly below search input with `--space-sm` gap. Results area below filters with `--space-lg` gap. No sidebar. No footer.

#### Full-Page Prompt
> A dark-themed code search page on a `--color-bg-primary` (#0d1117) background. At the top, a fixed 56px header bar with `--color-bg-secondary` background and bottom border — containing the "CodeContext" brand name with a code icon in blue on the left.
>
> Below the header (40px gap), centered in the page (max 960px wide): a prominent 44px-tall search input with dark background, subtle border, a search icon placeholder, and an attached blue "Search" button on the right.
>
> Directly below the search input (8px gap): a filters row containing a "Repository" dropdown (200px, showing "All repositories") on the left, and a horizontal row of language checkboxes (Java, Python, TypeScript, JavaScript, C, C++) to its right, each with a small 16px checkbox and label.
>
> Below the filters (24px gap): three result cards stacked vertically with 24px gaps. Each card has a dark card background (#161b22) with subtle border. Each card contains: a blue file-path link as the header, followed by small gray pills for repo name and language, and a relevance score percentage at the far right. Below the header, a purple symbol name. Below that, a code block with near-black background showing syntax-highlighted code in Monokai colors (red keywords, blue strings, purple functions, orange variables) with gray line numbers in a left gutter. Code block has a max height with scroll if needed.
>
> The overall feel is dense, technical, and focused — like GitHub's dark code search or Sourcegraph, designed for developers who want to quickly scan and evaluate code snippets.

#### Key Interactions
- Typing in search input and pressing Enter or clicking Search triggers query
- Repository dropdown filters to a single repo (passes `repo` parameter to FR-013)
- Language checkboxes filter by language (passes language filter to FR-018)
- Clicking file path link in result card could open source in new tab (future enhancement)
- Result cards show skeleton loaders during search (3 shimmer cards)

#### Responsive Behavior
- **Desktop (>= 1024px)**: Full layout as described, 960px content width centered
- **Tablet (768-1023px)**: Content width shrinks to 100% with 24px side padding. Language checkboxes wrap to 2 rows. Everything else unchanged.
- **Mobile (< 768px)**: Search button becomes full-width below input. Repo dropdown becomes full-width. Language checkboxes stack vertically. Result card code blocks scroll horizontally. Header brand name abbreviated.

---

## 5. Style Rules & Constraints

### 5.1 Accessibility
- All text meets WCAG AA contrast ratios (4.5:1 normal text, 3:1 large text) against their backgrounds
- Focus indicators visible on all interactive elements (blue border glow)
- Keyboard navigable: Tab through search → repo dropdown → language checkboxes → result cards
- Code blocks have `role="region"` with `aria-label` for screen readers

### 5.2 Animation
- **Transitions**: 150ms ease for hover states (borders, shadows, background colors)
- **Loading shimmer**: 1.5s linear infinite for skeleton loaders
- **No decorative animations** — developer tool should feel instant and responsive

### 5.3 Code Rendering
- Syntax highlighting uses the Monokai-inspired tokens defined in Section 2.1
- Line numbers always visible in code blocks
- Horizontal scroll for long lines (no wrapping of code)
- Max height 200px per code block with vertical scroll; "Show all" expands
- Monospace font (JetBrains Mono) for all code content

### 5.4 Information Density
- Maximize code visibility — minimize chrome and decoration
- No card shadows in default state — only on hover
- Compact metadata (badges, not full labels)
- Score displayed as percentage, color-coded by range
