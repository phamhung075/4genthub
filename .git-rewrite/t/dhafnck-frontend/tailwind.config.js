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
          border: 'var(--color-surface-border)',
          'border-hover': 'var(--color-surface-border-hover)',
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
        // Navigation Colors
        nav: {
          background: 'var(--color-nav-background)',
          text: 'var(--color-nav-text)',
          'text-hover': 'var(--color-nav-text-hover)',
          'text-active': 'var(--color-nav-text-active)',
          border: 'var(--color-nav-border)',
        },
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
      },
    },
  },
  plugins: [],
}

