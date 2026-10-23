import { createTheme, PaletteOptions, ThemeOptions } from '@mui/material/styles';
import { TokenMode, valueOf } from './tokenValues';

// The palette carries concrete colours, read out of theme.css per mode by
// tokenValues.ts - not `var()` strings. Six of the components this app mounts
// run colour maths on a palette value (Alert, Button, Checkbox, Divider,
// IconButton, a TextField with an adornment) and throw on `var()`, which unmounts
// the tree. theme.css stays the only place a value is authored; the palette is
// read from it, so light and dark differ in their values, not only in `mode`.
//
// Every palette colour names all four keys. `createTheme` would derive a missing
// sibling (contrastText from main) through parseColor, and a derivation is a
// value the token layer does not own.
type TokenTable = { readonly [key: string]: string | TokenTable };

/** Every palette leaf and the token it reads. The palette is built from this
 *  table and muiTheme.test.ts walks the built palette back against theme.css, so
 *  a colour typed in between the two is red by name, not by a near miss. */
export const paletteTokens: TokenTable = {
  primary: {
    main: '--color-primary',
    light: '--color-primary-light',
    dark: '--color-primary-dark',
    contrastText: '--color-accent-contrast',
  },
  // Secondary IS the accent (theme.css declares --color-secondary as
  // var(--color-accent) in both blocks), so it takes the same family and the
  // accent's contrast token. Left unnamed, MUI fills the slot with its own
  // default literal, which no token change would ever reach.
  secondary: {
    main: '--color-secondary',
    light: '--color-secondary-light',
    dark: '--color-secondary-dark',
    contrastText: '--color-accent-contrast',
  },
  background: { default: '--color-background', paper: '--color-surface' },
  text: {
    primary: '--color-text',
    secondary: '--color-text-secondary',
    disabled: '--color-text-disabled',
  },
  error: {
    main: '--color-error',
    light: '--color-error-light',
    dark: '--color-error-dark',
    contrastText: '--color-error-contrast',
  },
  warning: {
    main: '--color-warning',
    light: '--color-warning-light',
    dark: '--color-warning-dark',
    contrastText: '--color-warning-contrast',
  },
  success: {
    main: '--color-success',
    light: '--color-success-light',
    dark: '--color-success-dark',
    contrastText: '--color-success-contrast',
  },
  info: {
    main: '--color-info',
    light: '--color-info-light',
    dark: '--color-info-dark',
    contrastText: '--color-info-contrast',
  },
  divider: '--color-surface-border',
};

const valuesFor = (mode: TokenMode, node: TokenTable): Record<string, unknown> =>
  Object.fromEntries(
    Object.entries(node).map(([key, entry]) => [
      key,
      typeof entry === 'string' ? valueOf(mode, entry) : valuesFor(mode, entry),
    ]),
  );

const paletteFor = (mode: TokenMode) => ({
  mode,
  ...valuesFor(mode, paletteTokens),
} as PaletteOptions);

// Create MUI theme for light mode
export const lightTheme = createTheme({
  palette: paletteFor('light'),
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-surface-border)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-surface-border)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
        contained: {
          backgroundColor: 'var(--color-button-primary-bg)',
          color: 'var(--color-button-primary-text)',
          '&:hover': {
            backgroundColor: 'var(--color-button-primary-hover)',
          },
        },
        outlined: {
          borderColor: 'var(--color-button-outline-border)',
          '&:hover': {
            backgroundColor: 'var(--color-button-outline-hover)',
          },
        },
        text: {
          color: 'var(--color-text)',
          '&:hover': {
            backgroundColor: 'var(--color-background-hover)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: 'var(--color-input-background)',
            '& fieldset': {
              borderColor: 'var(--color-input-border)',
            },
            '&:hover fieldset': {
              borderColor: 'var(--color-input-border-focus)',
            },
            '&.Mui-focused fieldset': {
              borderColor: 'var(--color-input-border-focus)',
            },
          },
          '& .MuiInputBase-input': {
            color: 'var(--color-input-text)',
            '&::placeholder': {
              color: 'var(--color-input-placeholder)',
            },
            // Handle autofill to prevent browser default styles
            '&:-webkit-autofill': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
              transition: 'background-color 5000s ease-in-out 0s',
            },
            '&:-webkit-autofill:hover': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
            '&:-webkit-autofill:focus': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
            '&:-webkit-autofill:active': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-nav-background)',
          borderBottom: `1px solid ${'var(--color-nav-border)'}`,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: 'var(--color-surface)',
          borderRight: `1px solid ${'var(--color-surface-border)'}`,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: 'var(--color-surface-border)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${'var(--color-surface-border)'}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-background-secondary)',
        },
      },
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      color: 'var(--color-text)',
    },
    h2: {
      color: 'var(--color-text)',
    },
    h3: {
      color: 'var(--color-text)',
    },
    h4: {
      color: 'var(--color-text)',
    },
    h5: {
      color: 'var(--color-text)',
    },
    h6: {
      color: 'var(--color-text)',
    },
    body1: {
      color: 'var(--color-text)',
    },
    body2: {
      color: 'var(--color-text-secondary)',
    },
  },
} as ThemeOptions);

// Create MUI theme for dark mode
export const darkTheme = createTheme({
  palette: paletteFor('dark'),
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-surface-border)',
          backgroundImage: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-surface-border)',
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
        contained: {
          backgroundColor: 'var(--color-button-primary-bg)',
          color: 'var(--color-button-primary-text)',
          '&:hover': {
            backgroundColor: 'var(--color-button-primary-hover)',
          },
        },
        outlined: {
          borderColor: 'var(--color-button-outline-border)',
          color: 'var(--color-text)',
          '&:hover': {
            backgroundColor: 'var(--color-button-outline-hover)',
            borderColor: 'var(--color-button-outline-border)',
          },
        },
        text: {
          color: 'var(--color-text)',
          '&:hover': {
            backgroundColor: 'var(--color-background-hover)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: 'var(--color-input-background)',
            '& fieldset': {
              borderColor: 'var(--color-input-border)',
            },
            '&:hover fieldset': {
              borderColor: 'var(--color-input-border-focus)',
            },
            '&.Mui-focused fieldset': {
              borderColor: 'var(--color-input-border-focus)',
            },
          },
          '& .MuiInputBase-input': {
            color: 'var(--color-input-text)',
            '&::placeholder': {
              color: 'var(--color-input-placeholder)',
            },
            // Handle autofill to prevent browser default blue background
            '&:-webkit-autofill': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
              transition: 'background-color 5000s ease-in-out 0s',
            },
            '&:-webkit-autofill:hover': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
            '&:-webkit-autofill:focus': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
            '&:-webkit-autofill:active': {
              WebkitBoxShadow: `0 0 0 1000px ${'var(--color-input-background)'} inset`,
              WebkitTextFillColor: 'var(--color-input-text)',
            },
          },
          '& .MuiInputLabel-root': {
            color: 'var(--color-text-secondary)',
            '&.Mui-focused': {
              color: 'var(--color-primary)',
            },
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-nav-background)',
          borderBottom: `1px solid ${'var(--color-nav-border)'}`,
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: 'var(--color-surface)',
          borderRight: `1px solid ${'var(--color-surface-border)'}`,
          backgroundImage: 'none',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: 'var(--color-surface-border)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${'var(--color-surface-border)'}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-background-secondary)',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          color: 'var(--color-text)',
          '&:hover': {
            backgroundColor: 'var(--color-background-hover)',
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: 'var(--color-text-secondary)',
        },
      },
    },
    MuiRadio: {
      styleOverrides: {
        root: {
          color: 'var(--color-text-secondary)',
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          '& .MuiSwitch-track': {
            backgroundColor: 'var(--color-background-tertiary)',
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--color-background-tertiary)',
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: 'var(--color-primary)',
        },
      },
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      color: 'var(--color-text)',
    },
    h2: {
      color: 'var(--color-text)',
    },
    h3: {
      color: 'var(--color-text)',
    },
    h4: {
      color: 'var(--color-text)',
    },
    h5: {
      color: 'var(--color-text)',
    },
    h6: {
      color: 'var(--color-text)',
    },
    body1: {
      color: 'var(--color-text)',
    },
    body2: {
      color: 'var(--color-text-secondary)',
    },
  },
} as ThemeOptions);

// Helper function to get the current theme
export const getTheme = (mode: 'light' | 'dark') => {
  return mode === 'dark' ? darkTheme : lightTheme;
};
