import { createTheme, ThemeOptions } from '@mui/material/styles';

// One palette for both modes: every colour is a token reference, and the token
// layer in src/styles/theme.css is what resolves per mode, so light and dark
// differ only in `mode`. Nothing here is a colour value.
//
// Every palette colour carries all four keys. `createTheme` derives a missing
// sibling (contrastText from main) through parseColor, and parseColor cannot
// read var(), so an omitted key throws instead of guessing.
const paletteFor = (mode: 'light' | 'dark') => ({
  mode,
  primary: {
    main: 'var(--color-primary)',
    light: 'var(--color-primary-light)',
    dark: 'var(--color-primary-dark)',
    contrastText: 'var(--color-accent-contrast)',
  },
  background: {
    default: 'var(--color-background)',
    paper: 'var(--color-surface)',
  },
  text: {
    primary: 'var(--color-text)',
    secondary: 'var(--color-text-secondary)',
    disabled: 'var(--color-text-disabled)',
  },
  error: {
    main: 'var(--color-error)',
    light: 'var(--color-error-light)',
    dark: 'var(--color-error-dark)',
    contrastText: 'var(--color-error-contrast)',
  },
  warning: {
    main: 'var(--color-warning)',
    light: 'var(--color-warning-light)',
    dark: 'var(--color-warning-dark)',
    contrastText: 'var(--color-warning-contrast)',
  },
  success: {
    main: 'var(--color-success)',
    light: 'var(--color-success-light)',
    dark: 'var(--color-success-dark)',
    contrastText: 'var(--color-success-contrast)',
  },
  info: {
    main: 'var(--color-info)',
    light: 'var(--color-info-light)',
    dark: 'var(--color-info-dark)',
    contrastText: 'var(--color-info-contrast)',
  },
  divider: 'var(--color-surface-border)',
});

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
