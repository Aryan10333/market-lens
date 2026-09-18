# Look and feel

The app uses one small set of colours and components, so every page looks like part of the same
product. Everything is defined in `web/src/app/globals.css` and `web/src/components/`.

## Light, dark and system

- Three choices in the header: **Light**, **Dark**, **System** (follows the device setting).
- The choice is saved in the browser and applies to that browser only.
- A tiny script runs before the page is drawn, so the correct theme is already in place — the page
  never flashes white before turning dark.
- With **System** selected, changing the device setting changes the app immediately.

## Colours

Colours are named by **role**, not by colour, so the same name works in both themes:

| Token | Used for |
|---|---|
| `bg`, `surface`, `surface-2` | Page background, cards, insets |
| `line`, `line-strong` | Borders and dividers |
| `text`, `muted`, `faint` | Main text, secondary text, labels |
| `brand` | Buttons, links, the active page |
| `positive`, `negative`, `warning` | Gains, losses, attention |
| `scan-surge`, `scan-volume`, `scan-breakout`, `scan-high`, `scan-sector` | One colour per scanner |

Each has a matching `-soft` background, used behind badges and tags.

Only the values change between themes; the roles stay the same. Dark mode is not the light palette
inverted: the backgrounds are deep blue-grey and the accents are lightened so text stays readable.

### Colour meaning

- **Green means up, red means down** — used for price moves only, never for decoration.
- **Each scanner has its own colour**, shown as a dot beside its name and as a stripe on the
  signal's headline, so the five screens stay distinguishable at a glance.
- Colour is never the only signal: job status shows a dot **and** the word, and scanner names are
  always written out.

## Components (`web/src/components/ui.tsx`)

| Component | Purpose |
|---|---|
| `Card` | A titled panel; the basic block of every page |
| `Stat` | One headline number with a label and a supporting line |
| `Badge` | Small status label (`positive`, `negative`, `warning`, `brand`) |
| `ScannerTag` | Coloured dot + scanner name |
| `EmptyState` | "Nothing here", with an explanation of why that is normal |
| `StatusDot` | Green/red/amber dot for job status |
| `AppHeader` | Logo, navigation, theme toggle, account and log out |

## Typography and numbers

- Geist for text, Geist Mono for job names and rule versions.
- Numbers use `.tabular`, so digits keep the same width and columns line up.
- Money is shown as ₹ with Indian digit grouping (`₹1,24,500`), volumes as `2.4×`, moves as `4.3%`.

## Layout

- One centred column, at most 6xl wide, with 16px side padding at every screen size.
- Cards stack on a phone and sit two-up from medium screens.
- Tables scroll sideways inside their card rather than stretching the page.
- The header stays at the top while scrolling.

## Accessibility

- Text meets normal contrast levels in both themes.
- Every control has a visible focus ring.
- Icon-only buttons (the theme toggle) carry text labels for screen readers.
- The current page is marked with `aria-current`, and the theme buttons with `aria-pressed`.
