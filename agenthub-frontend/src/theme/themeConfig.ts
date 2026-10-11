// Global Theme Configuration
export const themeConfig = {
  light: {
    // Primary Colors. The hue IS the token layer's --color-accent (#4f46e5) and
    // --color-accent-hover (#4338ca): MUI's palette derives from that one accent
    // rather than carrying a second brand hue (R1). The light/dark sub-keys below
    // still name blues and feed only MUI's primary.light /.dark.
    primary: '#4f46e5', // the accent token
    primaryHover: '#4338ca', // the accent hover token
    primaryLight: '#dbeafe', // blue-100 - MUI primary.light, not yet derived
    primaryDark: '#1e40af', // blue-800 - MUI primary.dark, not yet derived

    // Secondary Colors: the secondary colour is the accent. The violet set that used
    // to live here is gone (R1); the CSS token layer already says
    // --color-secondary: var(--color-accent), and nothing renders color="secondary".

    // Background Colors
    background: '#ffffff',
    backgroundSecondary: '#f9fafb', // gray-50
    backgroundTertiary: '#f3f4f6', // gray-100
    backgroundHover: '#f9fafb', // gray-50
    backgroundActive: '#e5e7eb', // gray-200

    // Surface Colors (Cards, Papers, etc)
    surface: '#ffffff',
    surfaceHover: '#f9fafb', // gray-50
    surfaceBorder: '#e5e7eb', // gray-200
    surfaceBorderHover: '#d1d5db', // gray-300

    // Text Colors
    text: '#111827', // gray-900
    textSecondary: '#6b7280', // gray-500
    textTertiary: '#9ca3af', // gray-400
    textDisabled: '#d1d5db', // gray-300
    textInverse: '#ffffff',

    // Input Colors
    inputBackground: '#ffffff',
    inputBorder: '#d1d5db', // gray-300
    inputBorderFocus: '#3b82f6', // blue-500
    inputBorderError: '#ef4444', // red-500
    inputText: '#111827', // gray-900
    inputPlaceholder: '#9ca3af', // gray-400

    // Button Colors. These must stay equal to primary/primaryHover: the palette
    // test pins the match, and MUI renders the login button from them.
    buttonPrimaryBg: '#4f46e5', // the accent, pinned equal to primary
    buttonPrimaryHover: '#4338ca', // the accent hover, pinned equal to primaryHover
    buttonPrimaryText: '#ffffff',
    buttonSecondaryBg: '#e5e7eb', // gray-200
    buttonSecondaryHover: '#d1d5db', // gray-300
    buttonSecondaryText: '#374151', // gray-700
    buttonOutlineBorder: '#d1d5db', // gray-300
    buttonOutlineHover: '#e5e7eb', // gray-200
    buttonDangerBg: '#ef4444', // red-500
    buttonDangerHover: '#dc2626', // red-600

    // Status Colors
    success: '#10b981', // green-500
    successLight: '#d1fae5', // green-100
    successDark: '#059669', // green-600
    warning: '#f59e0b', // amber-500
    warningLight: '#fef3c7', // amber-100
    warningDark: '#d97706', // amber-600
    error: '#ef4444', // red-500
    errorLight: '#fee2e2', // red-100
    errorDark: '#dc2626', // red-600
    info: '#4f46e5', // the accent, pinned equal to primary
    infoLight: '#dbeafe', // blue-100
    infoDark: '#4338ca', // the accent hover, pinned equal to primaryHover

    // Shadow & Overlay
    shadow: 'rgba(0, 0, 0, 0.1)',
    shadowMedium: 'rgba(0, 0, 0, 0.15)',
    shadowLarge: 'rgba(0, 0, 0, 0.2)',
    overlay: 'rgba(0, 0, 0, 0.5)',

    // Scrollbar
    scrollbarTrack: '#f3f4f6', // gray-100
    scrollbarThumb: '#d1d5db', // gray-300
    scrollbarThumbHover: '#9ca3af', // gray-400

    // Code/Syntax
    codeBackground: '#f3f4f6', // gray-100
    codeBorder: '#e5e7eb', // gray-200
    codeText: '#111827', // gray-900

    // Navigation
    navBackground: '#ffffff',
    navText: '#6b7280', // gray-500
    navTextHover: '#111827', // gray-900
    navTextActive: '#3b82f6', // blue-500
    navBorder: '#e5e7eb', // gray-200
  },

  dark: {
    // Primary Colors: the dark --color-accent (#818cf8) and its hover (#a5b4fc).
    primary: '#818cf8', // the dark accent token
    primaryHover: '#a5b4fc', // the dark accent hover token
    primaryLight: '#1e3a8a', // blue-900 - MUI primary.light, not yet derived
    primaryDark: '#93c5fd', // blue-300 - MUI primary.dark, not yet derived

    // Secondary Colors: the secondary colour is the accent, in dark too (R1).

    // Background Colors
    background: '#0f172a', // slate-900
    backgroundSecondary: '#1e293b', // slate-800
    backgroundTertiary: '#334155', // slate-700
    backgroundHover: '#334155', // slate-700
    backgroundActive: '#475569', // slate-600

    // Surface Colors (Cards, Papers, etc)
    surface: '#1e293b', // slate-800
    surfaceHover: '#334155', // slate-700
    surfaceBorder: '#334155', // slate-700
    surfaceBorderHover: '#475569', // slate-600

    // Text Colors
    text: '#f1f5f9', // slate-100
    textSecondary: '#94a3b8', // slate-400
    textTertiary: '#64748b', // slate-500
    textDisabled: '#475569', // slate-600
    textInverse: '#0f172a', // slate-900

    // Input Colors
    inputBackground: '#0f172a', // slate-900 - darker for better dark mode appearance
    inputBorder: '#475569', // slate-600
    inputBorderFocus: '#60a5fa', // blue-400
    inputBorderError: '#f87171', // red-400
    inputText: '#f1f5f9', // slate-100
    inputPlaceholder: '#64748b', // slate-500

    // Button Colors
    buttonPrimaryBg: '#818cf8', // the dark accent, pinned equal to primary
    buttonPrimaryHover: '#a5b4fc', // the dark accent hover, pinned equal to primaryHover
    buttonPrimaryText: '#ffffff',
    buttonSecondaryBg: '#334155', // slate-700
    buttonSecondaryHover: '#475569', // slate-600
    buttonSecondaryText: '#e2e8f0', // slate-200
    buttonOutlineBorder: '#475569', // slate-600
    buttonOutlineHover: '#334155', // slate-700
    buttonDangerBg: '#dc2626', // red-600
    buttonDangerHover: '#ef4444', // red-500

    // Status Colors
    success: '#10b981', // green-500
    successLight: '#064e3b', // green-900
    successDark: '#34d399', // green-400
    warning: '#f59e0b', // amber-500
    warningLight: '#78350f', // amber-900
    warningDark: '#fbbf24', // amber-400
    error: '#ef4444', // red-500
    errorLight: '#7f1d1d', // red-900
    errorDark: '#f87171', // red-400
    info: '#818cf8', // the dark accent, pinned equal to primary
    infoLight: '#1e3a8a', // blue-900
    infoDark: '#a5b4fc', // the dark accent hover, pinned equal to primaryHover

    // Shadow & Overlay
    shadow: 'rgba(0, 0, 0, 0.3)',
    shadowMedium: 'rgba(0, 0, 0, 0.4)',
    shadowLarge: 'rgba(0, 0, 0, 0.5)',
    overlay: 'rgba(0, 0, 0, 0.7)',

    // Scrollbar
    scrollbarTrack: '#1e293b', // slate-800
    scrollbarThumb: '#475569', // slate-600
    scrollbarThumbHover: '#64748b', // slate-500

    // Code/Syntax
    codeBackground: '#1e293b', // slate-800
    codeBorder: '#334155', // slate-700
    codeText: '#e2e8f0', // slate-200

    // Navigation
    navBackground: '#1e293b', // slate-800
    navText: '#94a3b8', // slate-400
    navTextHover: '#f1f5f9', // slate-100
    navTextActive: '#60a5fa', // blue-400
    navBorder: '#334155', // slate-700
  }
};

// The palettes above are the source for the MUI theme in src/theme/muiTheme.ts
// only. Every CSS custom property the app renders with is declared in
// src/styles/theme.css, which is the single source for the token layer; nothing
// writes those variables from JavaScript any more.
