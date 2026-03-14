# Code Context Retrieval System — UCD Style Guide

**Date**: 2026-03-14
**Status**: Approved
**SRS Reference**: docs/plans/2026-03-14-code-context-retrieval-srs.md

## 1. Visual Style Direction

**Chosen Style**: Developer Dark — 深色沉浸式开发者风格

**Rationale**: Deep dark background with high-contrast syntax highlighting, designed for prolonged developer use. Draws from GitHub Code Search and VS Code Dark Theme aesthetics. The dark theme reduces visual fatigue during extended code searching sessions and provides optimal contrast for syntax-highlighted code snippets — the core content type of this application.

**Mood**: Immersive, professional, IDE-like. Deep blue-gray backgrounds with bright accent colors for interactive elements and syntax highlighting.

## 2. Style Tokens

### 2.1 Color Palette

| Token | Hex | Usage | Contrast Ratio |
|-------|-----|-------|----------------|
| --color-primary | #58A6FF | Primary actions, links, active states | 5.2:1 on #0D1117 |
| --color-primary-hover | #79C0FF | Hover state for primary elements | 6.8:1 on #0D1117 |
| --color-secondary | #8B949E | Secondary actions, muted accents | 4.6:1 on #0D1117 |
| --color-bg-primary | #0D1117 | Main page background | — |
| --color-bg-secondary | #161B22 | Card/panel background | — |
| --color-bg-tertiary | #21262D | Input fields, code block background | — |
| --color-text-primary | #E6EDF3 | Body text, headings | 13.2:1 on #0D1117 |
| --color-text-secondary | #8B949E | Captions, hints, metadata | 4.6:1 on #0D1117 |
| --color-text-muted | #6E7681 | Disabled text, placeholders | 3.2:1 on #0D1117 (large text only) |
| --color-success | #3FB950 | Success states, positive scores | 5.1:1 on #0D1117 |
| --color-warning | #D29922 | Warning states | 4.8:1 on #0D1117 |
| --color-error | #F85149 | Error states, validation failures | 4.7:1 on #0D1117 |
| --color-border | #30363D | Default borders, dividers | — |
| --color-border-focus | #58A6FF | Focused input borders | — |
| --color-score-high | #3FB950 | Relevance score ≥ 0.8 | — |
| --color-score-mid | #D29922 | Relevance score 0.6–0.8 | — |
| --color-score-low | #8B949E | Relevance score < 0.6 | — |

**Syntax Highlighting Palette**:

| Token | Hex | Usage |
|-------|-----|-------|
| --syntax-keyword | #FF7B72 | Keywords (if, class, return) |
| --syntax-string | #A5D6FF | String literals |
| --syntax-comment | #6E7681 | Comments |
| --syntax-function | #D2A8FF | Function/method names |
| --syntax-type | #79C0FF | Types, classes, interfaces |
| --syntax-variable | #FFA657 | Variables, parameters |
| --syntax-number | #79C0FF | Numeric literals |

### 2.2 Typography Scale

| Token | Font Family | Size | Weight | Line Height | Usage |
|-------|-------------|------|--------|-------------|-------|
| --font-heading-1 | -apple-system, "Segoe UI", sans-serif | 28px | 600 | 1.3 | Page title ("Code Context Search") |
| --font-heading-2 | -apple-system, "Segoe UI", sans-serif | 20px | 600 | 1.35 | Section headings |
| --font-heading-3 | -apple-system, "Segoe UI", sans-serif | 16px | 600 | 1.4 | Card titles (file path) |
| --font-body | -apple-system, "Segoe UI", sans-serif | 14px | 400 | 1.5 | Body text, metadata |
| --font-body-small | -apple-system, "Segoe UI", sans-serif | 12px | 400 | 1.5 | Captions, timestamps |
| --font-label | -apple-system, "Segoe UI", sans-serif | 12px | 500 | 1.4 | Form labels, filter tags |
| --font-code | "JetBrains Mono", "Fira Code", "Cascadia Code", monospace | 13px | 400 | 1.6 | Code snippets, symbols |

### 2.3 Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| --space-xs | 4px | Tight inner padding (tags, badges) |
| --space-sm | 8px | Default inner padding (buttons, inputs) |
| --space-md | 16px | Card padding, section gaps |
| --space-lg | 24px | Page section margins |
| --space-xl | 40px | Major layout breaks |
| --radius-sm | 6px | Buttons, inputs, tags |
| --radius-md | 8px | Cards, result panels |
| --radius-lg | 12px | Modals, dialogs |
| --shadow-sm | 0 1px 2px rgba(0,0,0,0.3) | Subtle depth |
| --shadow-md | 0 4px 12px rgba(0,0,0,0.4) | Cards, dropdowns |
| --shadow-lg | 0 8px 24px rgba(0,0,0,0.5) | Modals, overlays |
| --max-content-width | 960px | Search + results content area |
| --sidebar-width | 240px | Language filter sidebar (desktop) |

### 2.4 Iconography & Imagery

- **Icon style**: Outlined, rounded corners, 1.5px stroke weight
- **Icon library**: Lucide Icons (latest stable)
- **Icon size**: 16px inline with text, 20px in buttons, 24px standalone
- **Color treatment**: --color-text-secondary default, --color-primary on interactive hover
- **No illustrations/photography**: Developer tool — icons and text only

## 3. Component Prompts

### 3.1 Search Input

**SRS Trace**: FR-005, FR-006
**Variants**: default, focused, filled, error, loading

#### Base Prompt
> A wide search input field on a dark developer interface (--color-bg-primary #0D1117). The input has a --color-bg-tertiary #21262D fill, 1px --color-border #30363D border, --radius-sm 6px rounded corners, height 44px. A 16px Lucide "Search" icon in --color-text-muted #6E7681 sits 12px from the left edge. Placeholder text "Search code context... (natural language or symbol)" in --color-text-muted #6E7681, --font-body 14px sans-serif. The input spans the full --max-content-width 960px, centered horizontally.

#### Variant Prompts
> **Focused**: Border changes to 1px --color-border-focus #58A6FF with a subtle 0 0 0 3px rgba(88,166,255,0.15) glow. Placeholder text remains.
> **Filled**: Text in --color-text-primary #E6EDF3 replaces placeholder. A 16px Lucide "X" clear icon appears at right edge in --color-text-secondary #8B949E.
> **Error**: Border changes to 1px --color-error #F85149. Error message "Query must not be empty" in --color-error #F85149, --font-body-small 12px, appears 4px below input.
> **Loading**: A 2px horizontal progress bar in --color-primary #58A6FF animates along the bottom edge of the input.

#### Style Constraints
- Input height exactly 44px for comfortable click target
- Search icon always visible, never replaced by text
- Error text below input, never as tooltip

### 3.2 Language Filter

**SRS Trace**: FR-015
**Variants**: default, selected, hover, error

#### Base Prompt
> A horizontal row of filter chips/tags below the search input, on --color-bg-primary #0D1117. Each chip is a rounded pill (--radius-sm 6px, height 28px, --space-xs 4px vertical padding, --space-sm 8px horizontal padding) with --color-bg-tertiary #21262D background and 1px --color-border #30363D border. Text in --font-label 12px 500 weight --color-text-secondary #8B949E. Chips read: "All", "Java", "Python", "TypeScript", "JavaScript", "C", "C++". Leading chip "All" is selected by default.

#### Variant Prompts
> **Selected**: Chip background becomes --color-primary #58A6FF at 15% opacity (rgba(88,166,255,0.15)), border --color-primary #58A6FF, text --color-primary #58A6FF.
> **Hover**: Background lightens to --color-bg-tertiary #21262D with border --color-border #30363D brightening to #484F58.
> **Error (unsupported language)**: An inline alert appears below chips: Lucide "AlertCircle" 16px icon + "Unsupported language" text in --color-error #F85149, --font-body-small 12px.

#### Style Constraints
- Chips wrap to next line if viewport < 600px
- Only one language selected at a time (single-select); "All" deselects language filter
- Chip order: All first, then alphabetical

### 3.3 Result Card

**SRS Trace**: FR-012, FR-014
**Variants**: default, hover, expanded

#### Base Prompt
> A vertical result card on --color-bg-secondary #161B22 background, 1px --color-border #30363D border, --radius-md 8px corners, --space-md 16px padding, --shadow-sm. Full width within content area. Top row: file path in --font-heading-3 16px 600 weight --color-text-primary #E6EDF3 (e.g., "spring-framework / web / src/main/java/WebClient.java"), with a relevance score badge at far right. Second row: repository name + symbol name in --font-body-small 12px --color-text-secondary #8B949E (e.g., "spring-framework · WebClient.builder()"). Below: a code snippet block with --color-bg-tertiary #21262D background, --radius-sm 6px, --space-sm 8px padding, displaying syntax-highlighted code in --font-code 13px "JetBrains Mono". Line numbers in --color-text-muted #6E7681 at left margin.

#### Variant Prompts
> **Hover**: Border brightens to #484F58, --shadow-md replaces --shadow-sm.
> **Expanded**: Code snippet expands to show full content with a "Collapse" link in --color-primary #58A6FF at bottom right.

#### Style Constraints
- Code snippet max 8 lines in collapsed state, scrollable when expanded
- Score badge: pill shape, colored by relevance tier (--color-score-high/mid/low)
- Cards stack vertically with --space-md 16px gap between them

### 3.4 Score Badge

**SRS Trace**: FR-012
**Variants**: high (≥0.8), mid (0.6–0.8), low (<0.6)

#### Base Prompt
> A small pill-shaped badge, --radius-sm 6px, height 22px, --space-xs 4px vertical / --space-sm 8px horizontal padding. --font-label 12px 500 weight. Score displayed as decimal (e.g., "0.92"). Background is the score color at 15% opacity, text is the full score color.

#### Variant Prompts
> **High (≥0.8)**: Background rgba(63,185,80,0.15), text --color-score-high #3FB950.
> **Mid (0.6–0.8)**: Background rgba(210,153,34,0.15), text --color-score-mid #D29922.
> **Low (<0.6)**: Background rgba(139,148,158,0.15), text --color-score-low #8B949E.

### 3.5 Empty State

**SRS Trace**: FR-012 (zero results)
**Variants**: no-results, initial

#### Base Prompt
> Centered within the results area on --color-bg-primary #0D1117. A 48px Lucide "SearchX" icon in --color-text-muted #6E7681, centered. Below: "No results found" in --font-heading-2 20px 600 weight --color-text-primary #E6EDF3. Below that: "Try a different query or broaden your language filter" in --font-body 14px --color-text-secondary #8B949E. Vertical spacing --space-md 16px between elements.

#### Variant Prompts
> **Initial (before first search)**: Icon changes to Lucide "Code2" 48px. Heading: "Search code context". Subtext: "Enter a natural language query or code symbol to find relevant code snippets, documentation, and examples."

### 3.6 Error Alert

**SRS Trace**: FR-005, FR-006, FR-018
**Variants**: validation-error, auth-error

#### Base Prompt
> A horizontal alert bar spanning full content width, --color-bg-secondary #161B22 background with 1px left border in --color-error #F85149 (4px thick), --radius-md 8px corners, --space-md 16px padding. Left: Lucide "AlertCircle" 20px icon in --color-error #F85149. Right of icon: error message in --font-body 14px --color-text-primary #E6EDF3. Far right: Lucide "X" dismiss icon 16px in --color-text-secondary #8B949E.

#### Variant Prompts
> **Validation error**: Message reads "Query must not be empty" or "Unsupported language: [lang]. Supported: Java, Python, TypeScript, JavaScript, C, C++".
> **Auth error**: Message reads "Authentication required. Please log in to continue." with a --color-primary #58A6FF "Log in" link.

### 3.7 Login Form

**SRS Trace**: FR-018, FR-014
**Variants**: default, error, loading

#### Base Prompt
> A centered login card (width 400px) on --color-bg-primary #0D1117. Card: --color-bg-secondary #161B22, 1px --color-border #30363D, --radius-md 8px, --space-lg 24px padding, --shadow-md. Top: project logo/title "Code Context Search" in --font-heading-2 20px 600 weight --color-text-primary #E6EDF3, centered. Below --space-lg: "API Key" label in --font-label 12px 500 weight --color-text-secondary #8B949E. Below --space-xs: password-type input (same style as Search Input but full card width, height 40px). Below --space-md: primary button "Sign In" — full width, height 40px, --color-primary #58A6FF background, white text, --font-label 12px 500 weight, --radius-sm 6px.

#### Variant Prompts
> **Error**: Input border --color-error #F85149, "Invalid API key" text below in --color-error, --font-body-small 12px.
> **Loading**: Button text replaced by a 16px spinner, button opacity 0.7, disabled.

## 4. Page Prompts

### 4.1 Search Page

**SRS Trace**: FR-005, FR-006, FR-007, FR-012, FR-014, FR-015
**User Persona**: Software Developer
**Entry Points**: Direct URL access after authentication; redirect from Login Page

#### Layout Description
Single-column centered layout. Sticky header at top with branding. Main content area max-width 960px, centered. Search Input at top of content area, Language Filter chips below it, then a vertical stack of Result Cards. No sidebar on desktop; language filter is inline. On initial load, Empty State (initial variant) replaces result area.

#### Full-Page Prompt
> A dark-themed code search interface on --color-bg-primary #0D1117 full viewport. **Header**: 56px height, --color-bg-secondary #161B22 background, 1px --color-border #30363D bottom border. Left: Lucide "Code2" 24px icon in --color-primary #58A6FF + "Code Context Search" in --font-heading-3 16px 600 weight --color-text-primary #E6EDF3. Right: a subtle avatar circle 32px in --color-bg-tertiary #21262D with user initial letter. **Main content**: centered, --max-content-width 960px, --space-xl 40px top margin from header. **Search Input** component spans full width. Below --space-sm 8px: **Language Filter** chip row. Below --space-lg 24px: three **Result Card** components stacked vertically with --space-md 16px gaps, each showing a different code snippet with syntax highlighting (Java, Python, TypeScript). Each card has a **Score Badge** at top-right. Bottom of viewport: subtle footer text "Powered by Code Context Retrieval" in --font-body-small 12px --color-text-muted #6E7681, centered, --space-lg 24px from last card.

#### Key Interactions
- Typing in Search Input and pressing Enter or clicking search icon triggers query
- Clicking a Language Filter chip filters results; "All" resets filter
- Clicking a Result Card header (file path) could expand the code snippet
- Results load with skeleton placeholders (pulse animation on --color-bg-tertiary blocks)

#### Responsive Behavior
- **Desktop (≥ 1024px)**: Centered 960px content, all chips visible in one row
- **Tablet (768–1023px)**: Content area becomes 100% width with --space-md 16px horizontal padding, chips may wrap to two rows
- **Mobile (< 768px)**: Full-width layout, --space-sm 8px horizontal padding, chips wrap freely, code snippets horizontally scrollable, header collapses title to icon only

### 4.2 Login Page

**SRS Trace**: FR-018, FR-014
**User Persona**: Software Developer
**Entry Points**: Redirect from Search Page when unauthenticated; direct URL access

#### Layout Description
Full-viewport centered layout. Single Login Form card centered both horizontally and vertically on the dark background. No header, no footer — minimal distraction.

#### Full-Page Prompt
> A minimal dark login screen on --color-bg-primary #0D1117 covering the full viewport. Perfectly centered: the **Login Form** component (400px wide card). Above the card, --space-lg 24px: Lucide "Code2" 48px icon in --color-primary #58A6FF, centered. Below the form card, --space-md 16px: "Enter your API key to access Code Context Search" in --font-body 14px --color-text-secondary #8B949E, centered. The rest of the viewport is empty --color-bg-primary, creating a focused, distraction-free authentication experience. A subtle radial gradient (rgba(88,166,255,0.03)) emanates from center behind the card for depth.

#### Key Interactions
- Entering API key and pressing Enter or clicking "Sign In" submits authentication
- Invalid key shows inline error below input (Login Form error variant)
- Successful auth redirects to Search Page
- API key input is password-masked by default with a Lucide "Eye"/"EyeOff" toggle at right edge

#### Responsive Behavior
- **Desktop (≥ 1024px)**: Card centered, 400px width
- **Tablet (768–1023px)**: Card centered, 400px width (unchanged)
- **Mobile (< 768px)**: Card expands to full width with --space-md 16px horizontal margin, vertically centered

## 5. Style Rules & Constraints

### Accessibility
- All interactive elements meet WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text)
- --color-text-muted (#6E7681) only for large text (≥ 18px or ≥ 14px bold) or non-essential decorative text
- All interactive elements have visible focus indicators (--color-border-focus ring)
- Minimum touch target 44px height for inputs and buttons

### Animation
- Transitions: 150ms ease for color/border changes, 200ms ease for layout shifts
- Skeleton loading: pulse animation (opacity 0.3 → 0.7) on --color-bg-tertiary placeholder blocks
- No animation that exceeds 250ms or causes layout shift during loading
- Respect `prefers-reduced-motion` — disable all animations when set

### Dark Mode
- This is a dark-only interface; no light mode variant is required
- All colors are designed for dark backgrounds; do not invert

### Code Display
- Syntax highlighting uses the dedicated syntax palette (Section 2.1)
- Code blocks always use --font-code (JetBrains Mono fallback chain)
- Line numbers displayed in --color-text-muted, right-aligned, with --space-sm gap before code
- Horizontal scroll for long lines; no line wrapping in code blocks
- Max 8 visible lines in collapsed Result Card; expand to show full content
