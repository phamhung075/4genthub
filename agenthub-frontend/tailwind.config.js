/** @type {import('tailwindcss').Config} */

// Every theme colour below is a CSS custom property (src/styles/theme.css holds them as
// hex), so the property must be given an alpha channel at use time: Tailwind v3 drops an
// opacity-modified utility whose colour it cannot resolve, and a bare `var(--color-x)`
// has no channel to put one on. Mixing the property with transparent states the alpha -
// `<alpha-value>` is 1 for the solid form and the modifier for `bg-accent/15` - so one
// entry serves both and `border-accent/40` paints instead of vanishing.
// `--color-*` stays plain hex on purpose: a channel-triple token would break the 100-odd
// rules and inline styles that read the property as a complete colour.
const token = (name) =>
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
          DEFAULT: token('primary'),
          hover: token('primary-hover'),
          light: token('primary-light'),
          dark: token('primary-dark'),
        },
        // Secondary Colors
        secondary: {
          DEFAULT: token('secondary'),
          hover: token('secondary-hover'),
          light: token('secondary-light'),
          dark: token('secondary-dark'),
        },
        // Background Colors
        background: {
          DEFAULT: token('background'),
          secondary: token('background-secondary'),
          tertiary: token('background-tertiary'),
          hover: token('background-hover'),
          active: token('background-active'),
        },
        // Surface Colors
        surface: {
          DEFAULT: token('surface'),
          hover: token('surface-hover'),
          raised: token('surface-raised'),
          border: token('surface-border'),
          'border-hover': token('surface-border-hover'),
          'border-strong': token('surface-border-strong'),
        },
        // Text Colors
        text: {
          DEFAULT: token('text'),
          secondary: token('text-secondary'),
          tertiary: token('text-tertiary'),
          disabled: token('text-disabled'),
          inverse: token('text-inverse'),
        },
        // Input Colors
        input: {
          background: token('input-background'),
          border: token('input-border'),
          'border-focus': token('input-border-focus'),
          'border-error': token('input-border-error'),
          text: token('input-text'),
          placeholder: token('input-placeholder'),
        },
        // Button Colors
        button: {
          'primary-bg': token('button-primary-bg'),
          'primary-hover': token('button-primary-hover'),
          'primary-text': token('button-primary-text'),
          'secondary-bg': token('button-secondary-bg'),
          'secondary-hover': token('button-secondary-hover'),
          'secondary-text': token('button-secondary-text'),
          'outline-border': token('button-outline-border'),
          'outline-hover': token('button-outline-hover'),
          'danger-bg': token('button-danger-bg'),
          'danger-hover': token('button-danger-hover'),
        },
        // Status Colors
        success: {
          DEFAULT: token('success'),
          light: token('success-light'),
          dark: token('success-dark'),
        },
        warning: {
          DEFAULT: token('warning'),
          light: token('warning-light'),
          dark: token('warning-dark'),
        },
        error: {
          DEFAULT: token('error'),
          light: token('error-light'),
          dark: token('error-dark'),
        },
        info: {
          DEFAULT: token('info'),
          light: token('info-light'),
          dark: token('info-dark'),
        },
        // The one accent, and the source a chrome surface should paint from: the CSS
        // token layer declares it, Tailwind names it here, and MUI's palette names the
        // same value (R1), bound to the CSS by the token-parity test. A second hue in
        // the shell is therefore a defect rather than a style choice.
        accent: {
          DEFAULT: token('accent'),
          hover: token('accent-hover'),
          contrast: token('accent-contrast'),
        },
        // Navigation Colors
        nav: {
          background: token('nav-background'),
          text: token('nav-text'),
          'text-hover': token('nav-text-hover'),
          'text-active': token('nav-text-active'),
          border: token('nav-border'),
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
        'base': token('background'),
        'base-secondary': token('background-secondary'),
        'base-tertiary': token('background-tertiary'),
        'surface': token('surface'),
        'surface-hover': token('surface-hover'),
      },
      textColor: {
        'base': token('text'),
        'base-secondary': token('text-secondary'),
        'base-tertiary': token('text-tertiary'),
      },
      borderColor: {
        'base': token('surface-border'),
        'base-hover': token('surface-border-hover'),
        'surface-border': token('surface-border'),
        'surface-border-hover': token('surface-border-hover'),
        'nav-border': token('nav-border'),
        'button-outline-border': token('button-outline-border'),
        'input-border': token('input-border'),
        'input-border-focus': token('input-border-focus'),
        'input-border-error': token('input-border-error'),
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
