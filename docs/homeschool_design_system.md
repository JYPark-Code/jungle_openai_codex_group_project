# Homeschool Educational Platform Design System

## Reference Summary

- Attached image: bright dashboard with cool grays, a dark sidebar, thin dividers, and selective blue/green emphasis.
- Previous dashboard reference: useful for information architecture only, not for final color density.

## System Intent

This system should feel closer to a modern learning operating system than a playful pastel product. The visual center is neutral and disciplined, with color reserved for progress, active navigation, and status.

## Design Principles

1. Neutral first: large surfaces stay white, off-white, or light gray.
2. Controlled accent: blue is the primary signal color; green supports completion and progress.
3. Thin framing: borders should separate, not dominate.
4. Sharper geometry: use moderate radii only where grouping matters.
5. Dense but readable: the dashboard can hold a lot of information as long as hierarchy stays crisp.

## Color Tokens

### Core surfaces

- `--bg: #efefef`
- `--shell: #cfcfd1`
- `--surface: #ffffff`
- `--surface-soft: #f7f7f8`
- `--surface-muted: #f1f2f4`
- `--sidebar: #050505`
- `--line: rgba(17, 24, 39, 0.10)`
- `--line-strong: rgba(17, 24, 39, 0.16)`

### Typography

- `--text-strong: #111111`
- `--text-base: #262626`
- `--text-muted: #6f6f73`
- `--text-soft: #96979c`
- `--text-on-dark: #f5f7fb`

### Functional accents

- `--accent-primary: #2453ff`
- `--accent-primary-soft: #edf2ff`
- `--accent-progress: #b84dff`
- `--accent-success: #53c27b`
- `--accent-warn: #ffb020`

### Semantic mapping

- Primary action: `--accent-primary`
- Active navigation: `--accent-primary`
- Completed state: `--accent-success`
- In-progress state: `--accent-warn`
- Progress fill: `--accent-progress`

## Typography

- Display / section titles: `"Pretendard", "Avenir Next", sans-serif`
- Body / labels: `"Pretendard", "Apple SD Gothic Neo", sans-serif`
- Tone: semibold titles, compact metadata, quiet secondary copy

### Scale

- Hero section title: `30px / 1.1 / 700`
- Panel title: `16px / 1.3 / 700`
- Card title: `14px / 1.35 / 700`
- Body: `12px / 1.55 / 500`
- Metadata / caption: `11px / 1.4 / 500`

## Spacing and Radius

- Page outer padding: `24px`
- Shell padding: `0`
- Panel gutter: `16px`
- Card padding: `16px`
- Compact row padding: `10px 12px`
- Radius shell: `16px`
- Radius panel: `12px`
- Radius card: `10px`
- Radius small: `8px`

## Border and Elevation

- Standard border: `1px solid var(--line)`
- Emphasis border: `1px solid var(--line-strong)`
- Shell shadow: `0 18px 40px rgba(17, 24, 39, 0.08)`
- Card shadow: `0 4px 10px rgba(17, 24, 39, 0.04)`
- Hover: small shadow increase only, no floating-card effect

## Layout Model

### App shell

- 3 columns
- Sidebar: `160px`
- Main content: flexible
- Context rail: `220px`

### Main content pattern

- Header area with title and user summary
- Compact metric cards
- Two-column lesson progress modules
- Activity cards in a strict grid

## Component Rules

### Navigation item

- Height should stay between `36px` and `40px`
- Use dark sidebar with white text at low contrast by default
- Active state uses solid blue fill
- Corner radius should stay small

### Metric card

- White surface, thin gray border, small icon or illustration
- Short headline only
- No tinted full-card backgrounds

### Lesson progress card

- White panel with light dividers
- Blue chip action, purple progress fill, green status labels
- Large radius is not needed; use `10px` to `12px`

### Activity card

- Dense white tile with subtle bottom progress line
- Status chip should be pale and compact
- CTA stays secondary, usually as text or quiet button

### Calendar and schedule rail

- Prefer thin separators over filled blocks
- Use blue for current focus and green only for completed states

## Interaction Language

- Hover: background shifts slightly toward `--surface-soft`
- Focus: `2px` outline using `rgba(36, 83, 255, 0.22)`
- Pressed: reduce shadow and slightly darken blue controls
- Motion: `140ms` to `180ms`, ease-out

## Accessibility Guidance

- Keep blue actions readable on white with strong text contrast
- On the dark sidebar, avoid low-opacity text below practical readability
- Progress and status must pair color with labels

## Recommended Use In This Repo

- Use this system for dashboard and study-progress flows
- Prefer neutral surfaces with selective blue emphasis across new templates
- Avoid soft pastel fills unless a specific educational illustration needs them
