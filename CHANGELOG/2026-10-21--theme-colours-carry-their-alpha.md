# Theme colours carry their alpha, so an opacity-modified token class paints

The owner ruled on 2026-10-21 (board task `470c7439` Progress 6): fix the colour registration
app-wide rather than the panel's classes, and return the room picker to 40px/14px. Both landed on
branch `4genthub-min/fe-tw-alpha`.

### Fixed

- **`bg-accent/15`, `border-accent/40`, `bg-surface/80` and every other opacity-modified theme
  utility compile to a rule** - `agenthub-frontend/tailwind.config.js`: each of the 77 entries that
  read a `var(--color-*)` property now goes through one helper,
  `token(name) = color-mix(in srgb, var(--color-<name>) calc(<alpha-value> * 100%), transparent)`.
  Tailwind v3 parses a colour to place an alpha on it and silently drops the declaration when it
  cannot; `rgb(from …)`/`color-mix(…)` with `<alpha-value>` is the string form it hands the opacity
  to, so the solid form (`<alpha-value>` = 1) and the tinted form (`/40`, `/[0.03]`) come from one
  declaration. The token layer is untouched: `src/styles/theme.css` keeps plain hex, because a
  channel-triple token would break the ~100 rules that read the property as a complete colour, the
  65 inline writes from `src/theme/themeConfig.ts`, and the e2e reads of `--color-accent`.
  Measured with the Tailwind CLI (`-c tailwind.config.js -i <@tailwind directives> -o /tmp/…`) over
  the real `src`: opacity-modified theme classes 38, dead 38 before and 0 after; `.border-accent\/40`,
  `.bg-accent\/15` and `.bg-surface\/80` each emit their rule. No local vite build was run.
- **The room picker is 40px high with 14px text again** - `agenthub-frontend/src/components/RoomDecisionPanel.tsx`:
  the panel's size overrides (`text-xs py-1.5 h-auto min-h-[2.25rem]`) are gone, so the control keeps
  the `ui/select-simple` primitive's `min-h-[2.5rem] py-2 px-3 text-sm` as acceptance item 1 states.
  Measured in Chromium against the compiled stylesheet with the panel's class list: height 40px,
  font-size 14px (12px with the removed classes).

### Changed

- **A computed colour read by the shell audit accepts both spellings** - `agenthub-frontend/e2e/shell.spec.ts`:
  a colour resolved through `color-mix()` is serialized by Chromium as `color(srgb r g b / a)`, not
  `rgb(r, g, b)`, so the navigation's hue collector reads both and normalizes to the legacy triple
  (`0.309804 × 255` → 79, rounded). Without it the collected set is empty and the one-accent
  assertion at ≥1024 fails for a spelling, not a hue.

### Testing

`npx tsc --noEmit -p .` exit 0 (`agenthub-frontend`). The changed e2e spec typechecks on its own
(`tsc --noEmit --module node16 --moduleResolution node16 --strict --skipLibCheck e2e/shell.spec.ts`).
CSS emission and the picker measurement are the checks above; `npx vitest run` was not run, per the
owner ruling's "tsc only, no local build/test". The browser check on a deployed origin is pending the
lead's frontend deploy.
