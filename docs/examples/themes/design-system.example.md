# <Product> — Design system

New screens and changes use this file. A value it does not list needs a stated reason. Tokens live in `<path to the token stylesheet>`; use them by name, never as literal values.

## Colour roles

| Role | Token | Use for |
|---|---|---|
| Primary | `--color-primary`, `--color-primary-hover`, `--color-primary-light` | primary actions, selection, links, and the first data series |
| Secondary | `--color-secondary` | the second data series; secondary emphasis |
| Surfaces | `--color-surface`, `--color-card`, `--color-border` | page, cards, dividers |
| Text | `--color-text-primary`, `--color-text-secondary` | body, secondary text |
| Status | `--color-success`, `--color-error`, `--color-warning` | **status only**: chips, toasts, banners |

**Data visualisation.** Charts use primary, then secondary, then a neutral for "other". Status colours are never data colours. Colour is never the only signal: keep the label.

**Contrast.** Every text token meets the WCAG AA contrast ratio on the surfaces it is used on (4.5:1 for body text, 3:1 for large text). A muted text colour that fails it is not used for information a user needs.

## Type, spacing, shape

- Font: `<family>`; monospace `<family>` for codes.
- Spacing scale: `<xs> <sm> <md> <lg> <xl>`. No other spacing values.
- Radius: `<control>` for controls, `<card>` for cards.

## Components to reuse

- Lists: `<table component>`, `<filter bar>`, `<status badge>`.
- States: `<empty state>`, `<error banner with retry>`, `<loading skeleton>`.
- Page frame: breadcrumb, title and one-line description, then content.

## Layout

- Breakpoints `<tablet>` and `<desktop>`. At tablet width content reflows to one column; nothing scrolls horizontally except a table inside its own card.
