/** @type {import('tailwindcss').Config} */

// Every theme colour below is a CSS custom property (src/styles/theme.css holds them as
// hex), so the property must be given an alpha channel at use time: Tailwind v3 drops an
// opacity-modified utility whose colour it cannot resolve, and a bare `var(--color-x)`
// has no channel to put one on. Mixing the property with transparent states the alpha -
// `<alpha-value>` is 1 for the solid form and the modifier for `bg-accent/15` - so one
// entry serves both and `border-accent/40` paints instead of vanishing.
// `--color-*` stays plain hex on purpose: a channel-triple token would break the 100-odd
// rules and inline styles that read the property as a complete colour.
const withAlpha = (name) =>
  `color-mix(in srgb, var(--color-${name}) calc(<alpha-value> * 100%), transparent)`;

module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx,scss,css}"
  ],
  theme: {
    extend: {
      colors: {
        // Primary Colors
        primary: {
          DEFAULT: withAlpha('primary'),
          hover: withAlpha('primary-hover'),
          light: withAlpha('primary-light'),
          dark: withAlpha('primary-dark'),
        },
        // Secondary Colors
        secondary: {
          DEFAULT: withAlpha('secondary'),
          hover: withAlpha('secondary-hover'),
          light: withAlpha('secondary-light'),
          dark: withAlpha('secondary-dark'),
        },
        // Background Colors
        background: {
          DEFAULT: withAlpha('background'),
          secondary: withAlpha('background-secondary'),
          tertiary: withAlpha('background-tertiary'),
          hover: withAlpha('background-hover'),
          active: withAlpha('background-active'),
        },
        // Surface Colors
        surface: {
          DEFAULT: withAlpha('surface'),
          hover: withAlpha('surface-hover'),
          raised: withAlpha('surface-raised'),
          border: withAlpha('surface-border'),
          'border-hover': withAlpha('surface-border-hover'),
          'border-strong': withAlpha('surface-border-strong'),
        },
        // Text Colors
        text: {
          DEFAULT: withAlpha('text'),
          secondary: withAlpha('text-secondary'),
          tertiary: withAlpha('text-tertiary'),
          disabled: withAlpha('text-disabled'),
          inverse: withAlpha('text-inverse'),
        },
        // Input Colors
        input: {
          background: withAlpha('input-background'),
          border: withAlpha('input-border'),
          'border-focus': withAlpha('input-border-focus'),
          'border-error': withAlpha('input-border-error'),
          text: withAlpha('input-text'),
          placeholder: withAlpha('input-placeholder'),
        },
        // Button Colors
        button: {
          'primary-bg': withAlpha('button-primary-bg'),
          'primary-hover': withAlpha('button-primary-hover'),
          'primary-text': withAlpha('button-primary-text'),
          'secondary-bg': withAlpha('button-secondary-bg'),
          'secondary-hover': withAlpha('button-secondary-hover'),
          'secondary-text': withAlpha('button-secondary-text'),
          'outline-border': withAlpha('button-outline-border'),
          'outline-hover': withAlpha('button-outline-hover'),
          'danger-bg': withAlpha('button-danger-bg'),
          'danger-hover': withAlpha('button-danger-hover'),
        },
        // Status Colors
        success: {
          DEFAULT: withAlpha('success'),
          light: withAlpha('success-light'),
          dark: withAlpha('success-dark'),
        },
        warning: {
          DEFAULT: withAlpha('warning'),
          light: withAlpha('warning-light'),
          dark: withAlpha('warning-dark'),
        },
        error: {
          DEFAULT: withAlpha('error'),
          light: withAlpha('error-light'),
          dark: withAlpha('error-dark'),
        },
        info: {
          DEFAULT: withAlpha('info'),
          light: withAlpha('info-light'),
          dark: withAlpha('info-dark'),
        },
        // The one accent, and the source a chrome surface should paint from: the CSS
        // token layer declares it, Tailwind names it here, and MUI's palette names the
        // same value (R1), bound to the CSS by the token-parity test. A second hue in
        // the shell is therefore a defect rather than a style choice.
        accent: {
          DEFAULT: withAlpha('accent'),
          hover: withAlpha('accent-hover'),
          contrast: withAlpha('accent-contrast'),
        },
        // Navigation Colors
        nav: {
          background: withAlpha('nav-background'),
          text: withAlpha('nav-text'),
          'text-hover': withAlpha('nav-text-hover'),
          'text-active': withAlpha('nav-text-active'),
          border: withAlpha('nav-border'),
        },
      },
      // The type scale: eight steps, each a size over its own line height. The
      // product reads at text-body-sm (13/18); pages opt into the scale as their
      // slice lands instead of the scale changing under every page at once.
      fontSize: {
        'micro': ['11px', '16px'],
        'caption': ['12px', '16px'],
        'body-sm': ['13px', '18px'],
        'body': ['14px', '20px'],
        'title': ['16px', '24px'],
        'section': ['18px', '26px'],
        'page': ['20px', '28px'],
        'hero': ['24px', '32px'],
      },
      backgroundColor: {
        'base': withAlpha('background'),
        'base-secondary': withAlpha('background-secondary'),
        'base-tertiary': withAlpha('background-tertiary'),
        // No 'surface'/'surface-hover' aliases here: an alias whose name is the
        // ROOT of a nested tree in `colors` replaces that subtree as a whole, so
        // `bg-surface-raised` and `bg-surface-border*` registered nothing. The
        // nested entries already name surface.DEFAULT and surface.hover.
      },
      textColor: {
        // The primary text colour. `text-base` cannot carry it: it is also the default font size, so the
        // one class would set 16px where a call site only meant the colour. The retired `text-foreground`
        // maps onto this key (RULING 2026-10-22, map row 3), and the census test fails if it stops
        // compiling to a colour.
        'base-primary': withAlpha('text'),
        'base': withAlpha('text'),
        'base-secondary': withAlpha('text-secondary'),
        'base-tertiary': withAlpha('text-tertiary'),
      },
      borderColor: {
        'base': withAlpha('surface-border'),
        'base-hover': withAlpha('surface-border-hover'),
        'surface-border': withAlpha('surface-border'),
        'surface-border-hover': withAlpha('surface-border-hover'),
        'nav-border': withAlpha('nav-border'),
        'button-outline-border': withAlpha('button-outline-border'),
        'input-border': withAlpha('input-border'),
        'input-border-focus': withAlpha('input-border-focus'),
        'input-border-error': withAlpha('input-border-error'),
      },
      boxShadow: {
        'sm': '0 1px 2px 0 var(--color-shadow)',
        'DEFAULT': '0 1px 3px 0 var(--color-shadow), 0 1px 2px 0 var(--color-shadow)',
        'md': '0 4px 6px -1px var(--color-shadow-medium), 0 2px 4px -1px var(--color-shadow)',
        'lg': '0 10px 15px -3px var(--color-shadow-medium), 0 4px 6px -2px var(--color-shadow)',
        'xl': '0 20px 25px -5px var(--color-shadow-large), 0 10px 10px -5px var(--color-shadow-medium)',
        '2xl': '0 25px 50px -12px var(--color-shadow-large)',
      },
      borderRadius: {
        'none': '0',
        'sm': '0.125rem',
        'DEFAULT': '0.5rem',
        'md': '0.75rem',
        'lg': '1rem',
        'xl': '1.25rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        'full': '9999px',
        // The shape system, named: controls 6, inputs 8, cards and panels 12,
        // and pills for status only. The numbered keys above stay as they are so
        // this lands as a system to migrate to rather than a global restyle.
        'control': 'var(--radius-control)',
        'input': 'var(--radius-input)',
        'card': 'var(--radius-card)',
        'pill': 'var(--radius-pill)',
      },
      transitionDuration: {
        'fast': 'var(--motion-fast)',
        'state': 'var(--motion-state)',
        'panel': 'var(--motion-panel)',
      },
      transitionTimingFunction: {
        'standard': 'var(--motion-curve)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      keyframes: {
        "slide-in-from-right-full": {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
      },
      animation: {
        "in": "slide-in-from-right-full 0.3s ease-out",
      },
    },
  },
  plugins: [],
}
