import { createTheme, ThemeOptions } from '@mui/material/styles';
import { themeConfig } from './themeConfig';

// Create MUI theme for light mode
export const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: themeConfig.light.primary,
      light: themeConfig.light.primaryLight,
      dark: themeConfig.light.primaryDark,
    },
    secondary: {
      main: themeConfig.light.secondary,
      light: themeConfig.light.secondaryLight,
      dark: themeConfig.light.secondaryDark,
    },
    background: {
      default: themeConfig.light.background,
      paper: themeConfig.light.surface,
    },
    text: {
      primary: themeConfig.light.text,
      secondary: themeConfig.light.textSecondary,
      disabled: themeConfig.light.textDisabled,
    },
    error: {
      main: themeConfig.light.error,
      light: themeConfig.light.errorLight,
      dark: themeConfig.light.errorDark,
    },
    warning: {
      main: themeConfig.light.warning,
      light: themeConfig.light.warningLight,
      dark: themeConfig.light.warningDark,
    },
    success: {
      main: themeConfig.light.success,
      light: themeConfig.light.successLight,
      dark: themeConfig.light.successDark,
    },
    info: {
      main: themeConfig.light.info,
      light: themeConfig.light.infoLight,
      dark: themeConfig.light.infoDark,
    },
    divider: themeConfig.light.surfaceBorder,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.light.surface,
          borderColor: themeConfig.light.surfaceBorder,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.light.surface,
          borderColor: themeConfig.light.surfaceBorder,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
        contained: {
          backgroundColor: themeConfig.light.buttonPrimaryBg,
          color: themeConfig.light.buttonPrimaryText,
          '&:hover': {
            backgroundColor: themeConfig.light.buttonPrimaryHover,
          },
        },
        outlined: {
          borderColor: themeConfig.light.buttonOutlineBorder,
          '&:hover': {
            backgroundColor: themeConfig.light.buttonOutlineHover,
          },
        },
        text: {
          color: themeConfig.light.text,
          '&:hover': {
            backgroundColor: themeConfig.light.backgroundHover,
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: themeConfig.light.inputBackground,
            '& fieldset': {
              borderColor: themeConfig.light.inputBorder,
            },
            '&:hover fieldset': {
              borderColor: themeConfig.light.inputBorderFocus,
            },
            '&.Mui-focused fieldset': {
              borderColor: themeConfig.light.inputBorderFocus,
            },
          },
          '& .MuiInputBase-input': {
            color: themeConfig.light.inputText,
            '&::placeholder': {
              color: themeConfig.light.inputPlaceholder,
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
          backgroundColor: themeConfig.light.navBackground,
          borderBottom: `1px solid ${themeConfig.light.navBorder}`,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: themeConfig.light.surface,
          borderRight: `1px solid ${themeConfig.light.surfaceBorder}`,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: themeConfig.light.surfaceBorder,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${themeConfig.light.surfaceBorder}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.light.backgroundSecondary,
        },
      },
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      color: themeConfig.light.text,
    },
    h2: {
      color: themeConfig.light.text,
    },
    h3: {
      color: themeConfig.light.text,
    },
    h4: {
      color: themeConfig.light.text,
    },
    h5: {
      color: themeConfig.light.text,
    },
    h6: {
      color: themeConfig.light.text,
    },
    body1: {
      color: themeConfig.light.text,
    },
    body2: {
      color: themeConfig.light.textSecondary,
    },
  },
} as ThemeOptions);

// Create MUI theme for dark mode
export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: themeConfig.dark.primary,
      light: themeConfig.dark.primaryLight,
      dark: themeConfig.dark.primaryDark,
    },
    secondary: {
      main: themeConfig.dark.secondary,
      light: themeConfig.dark.secondaryLight,
      dark: themeConfig.dark.secondaryDark,
    },
    background: {
      default: themeConfig.dark.background,
      paper: themeConfig.dark.surface,
    },
    text: {
      primary: themeConfig.dark.text,
      secondary: themeConfig.dark.textSecondary,
      disabled: themeConfig.dark.textDisabled,
    },
    error: {
      main: themeConfig.dark.error,
      light: themeConfig.dark.errorLight,
      dark: themeConfig.dark.errorDark,
    },
    warning: {
      main: themeConfig.dark.warning,
      light: themeConfig.dark.warningLight,
      dark: themeConfig.dark.warningDark,
    },
    success: {
      main: themeConfig.dark.success,
      light: themeConfig.dark.successLight,
      dark: themeConfig.dark.successDark,
    },
    info: {
      main: themeConfig.dark.info,
      light: themeConfig.dark.infoLight,
      dark: themeConfig.dark.infoDark,
    },
    divider: themeConfig.dark.surfaceBorder,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.dark.surface,
          borderColor: themeConfig.dark.surfaceBorder,
          backgroundImage: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.dark.surface,
          borderColor: themeConfig.dark.surfaceBorder,
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
          backgroundColor: themeConfig.dark.buttonPrimaryBg,
          color: themeConfig.dark.buttonPrimaryText,
          '&:hover': {
            backgroundColor: themeConfig.dark.buttonPrimaryHover,
          },
        },
        outlined: {
          borderColor: themeConfig.dark.buttonOutlineBorder,
          color: themeConfig.dark.text,
          '&:hover': {
            backgroundColor: themeConfig.dark.buttonOutlineHover,
            borderColor: themeConfig.dark.buttonOutlineBorder,
          },
        },
        text: {
          color: themeConfig.dark.text,
          '&:hover': {
            backgroundColor: themeConfig.dark.backgroundHover,
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: themeConfig.dark.inputBackground,
            '& fieldset': {
              borderColor: themeConfig.dark.inputBorder,
            },
            '&:hover fieldset': {
              borderColor: themeConfig.dark.inputBorderFocus,
            },
            '&.Mui-focused fieldset': {
              borderColor: themeConfig.dark.inputBorderFocus,
            },
          },
          '& .MuiInputBase-input': {
            color: themeConfig.dark.inputText,
            '&::placeholder': {
              color: themeConfig.dark.inputPlaceholder,
            },
          },
          '& .MuiInputLabel-root': {
            color: themeConfig.dark.textSecondary,
            '&.Mui-focused': {
              color: themeConfig.dark.primary,
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
          backgroundColor: themeConfig.dark.navBackground,
          borderBottom: `1px solid ${themeConfig.dark.navBorder}`,
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: themeConfig.dark.surface,
          borderRight: `1px solid ${themeConfig.dark.surfaceBorder}`,
          backgroundImage: 'none',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: themeConfig.dark.surfaceBorder,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: `1px solid ${themeConfig.dark.surfaceBorder}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.dark.backgroundSecondary,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          color: themeConfig.dark.text,
          '&:hover': {
            backgroundColor: themeConfig.dark.backgroundHover,
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: themeConfig.dark.textSecondary,
        },
      },
    },
    MuiRadio: {
      styleOverrides: {
        root: {
          color: themeConfig.dark.textSecondary,
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        root: {
          '& .MuiSwitch-track': {
            backgroundColor: themeConfig.dark.backgroundTertiary,
          },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          backgroundColor: themeConfig.dark.backgroundTertiary,
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: themeConfig.dark.primary,
        },
      },
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      color: themeConfig.dark.text,
    },
    h2: {
      color: themeConfig.dark.text,
    },
    h3: {
      color: themeConfig.dark.text,
    },
    h4: {
      color: themeConfig.dark.text,
    },
    h5: {
      color: themeConfig.dark.text,
    },
    h6: {
      color: themeConfig.dark.text,
    },
    body1: {
      color: themeConfig.dark.text,
    },
    body2: {
      color: themeConfig.dark.textSecondary,
    },
  },
} as ThemeOptions);

// Helper function to get the current theme
export const getTheme = (mode: 'light' | 'dark') => {
  return mode === 'dark' ? darkTheme : lightTheme;
};