/** @type {import('tailwindcss').Config} */
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
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          light: 'var(--color-primary-light)',
          dark: 'var(--color-primary-dark)',
        },
        // Secondary Colors
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          hover: 'var(--color-secondary-hover)',
          light: 'var(--color-secondary-light)',
          dark: 'var(--color-secondary-dark)',
        },
        // Background Colors
        background: {
          DEFAULT: 'var(--color-background)',
          secondary: 'var(--color-background-secondary)',
          tertiary: 'var(--color-background-tertiary)',
          hover: 'var(--color-background-hover)',
          active: 'var(--color-background-active)',
        },
        // Surface Colors
        surface: {
          DEFAULT: 'var(--color-surface)',
          hover: 'var(--color-surface-hover)',
          raised: 'var(--color-surface-raised)',
          border: 'var(--color-surface-border)',
          'border-hover': 'var(--color-surface-border-hover)',
          'border-strong': 'var(--color-surface-border-strong)',
        },
        // Text Colors
        text: {
          DEFAULT: 'var(--color-text)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          disabled: 'var(--color-text-disabled)',
          inverse: 'var(--color-text-inverse)',
        },
        // Input Colors
        input: {
          background: 'var(--color-input-background)',
          border: 'var(--color-input-border)',
          'border-focus': 'var(--color-input-border-focus)',
          'border-error': 'var(--color-input-border-error)',
          text: 'var(--color-input-text)',
          placeholder: 'var(--color-input-placeholder)',
        },
        // Button Colors
        button: {
          'primary-bg': 'var(--color-button-primary-bg)',
          'primary-hover': 'var(--color-button-primary-hover)',
          'primary-text': 'var(--color-button-primary-text)',
          'secondary-bg': 'var(--color-button-secondary-bg)',
          'secondary-hover': 'var(--color-button-secondary-hover)',
          'secondary-text': 'var(--color-button-secondary-text)',
          'outline-border': 'var(--color-button-outline-border)',
          'outline-hover': 'var(--color-button-outline-hover)',
          'danger-bg': 'var(--color-button-danger-bg)',
          'danger-hover': 'var(--color-button-danger-hover)',
        },
        // Status Colors
        success: {
          DEFAULT: 'var(--color-success)',
          light: 'var(--color-success-light)',
          dark: 'var(--color-success-dark)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          light: 'var(--color-warning-light)',
          dark: 'var(--color-warning-dark)',
        },
        error: {
          DEFAULT: 'var(--color-error)',
          light: 'var(--color-error-light)',
          dark: 'var(--color-error-dark)',
        },
        info: {
          DEFAULT: 'var(--color-info)',
          light: 'var(--color-info-light)',
          dark: 'var(--color-info-dark)',
        },
        // The one accent, and the source a chrome surface should paint from: the CSS
        // token layer declares it, Tailwind names it here, and MUI's palette names the
        // same value (R1), bound to the CSS by the token-parity test. A second hue in
        // the shell is therefore a defect rather than a style choice.
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          contrast: 'var(--color-accent-contrast)',
        },
        // Navigation Colors
        nav: {
          background: 'var(--color-nav-background)',
          text: 'var(--color-nav-text)',
          'text-hover': 'var(--color-nav-text-hover)',
          'text-active': 'var(--color-nav-text-active)',
          border: 'var(--color-nav-border)',
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
        'base': 'var(--color-background)',
        'base-secondary': 'var(--color-background-secondary)',
        'base-tertiary': 'var(--color-background-tertiary)',
        'surface': 'var(--color-surface)',
        'surface-hover': 'var(--color-surface-hover)',
      },
      textColor: {
        'base': 'var(--color-text)',
        'base-secondary': 'var(--color-text-secondary)',
        'base-tertiary': 'var(--color-text-tertiary)',
      },
      borderColor: {
        'base': 'var(--color-surface-border)',
        'base-hover': 'var(--color-surface-border-hover)',
        'surface-border': 'var(--color-surface-border)',
        'surface-border-hover': 'var(--color-surface-border-hover)',
        'nav-border': 'var(--color-nav-border)',
        'button-outline-border': 'var(--color-button-outline-border)',
        'input-border': 'var(--color-input-border)',
        'input-border-focus': 'var(--color-input-border-focus)',
        'input-border-error': 'var(--color-input-border-error)',
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
