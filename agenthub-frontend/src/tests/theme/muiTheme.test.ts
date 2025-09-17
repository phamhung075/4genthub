import { createTheme } from '@mui/material/styles';
import { lightTheme, darkTheme, getTheme } from '../../theme/muiTheme';
import { themeConfig } from '../../theme/themeConfig';

// Mock dependencies
jest.mock('@mui/material/styles', () => ({
  createTheme: jest.fn((options) => ({ ...options, isTheme: true })),
}));

jest.mock('../../theme/themeConfig', () => ({
  themeConfig: {
    light: {
      primary: '#1976d2',
      primaryLight: '#42a5f5',
      primaryDark: '#1565c0',
      secondary: '#dc004e',
      secondaryLight: '#e33371',
      secondaryDark: '#9a0036',
      background: '#ffffff',
      surface: '#f5f5f5',
      text: '#000000',
      textSecondary: '#666666',
      textDisabled: '#999999',
      error: '#f44336',
      errorLight: '#e57373',
      errorDark: '#d32f2f',
      warning: '#ff9800',
      warningLight: '#ffb74d',
      warningDark: '#f57c00',
      success: '#4caf50',
      successLight: '#81c784',
      successDark: '#388e3c',
      info: '#2196f3',
      infoLight: '#64b5f6',
      infoDark: '#1976d2',
      surfaceBorder: '#e0e0e0',
      buttonPrimaryBg: '#1976d2',
      buttonPrimaryText: '#ffffff',
      buttonPrimaryHover: '#1565c0',
      buttonOutlineBorder: '#1976d2',
      buttonOutlineHover: 'rgba(25, 118, 210, 0.04)',
      backgroundHover: 'rgba(0, 0, 0, 0.04)',
      inputBackground: '#ffffff',
      inputBorder: '#e0e0e0',
      inputBorderFocus: '#1976d2',
      inputText: '#000000',
      inputPlaceholder: '#999999',
      navBackground: '#ffffff',
      navBorder: '#e0e0e0',
      backgroundSecondary: '#f5f5f5',
    },
    dark: {
      primary: '#90caf9',
      primaryLight: '#e3f2fd',
      primaryDark: '#42a5f5',
      secondary: '#f48fb1',
      secondaryLight: '#ffc1e3',
      secondaryDark: '#bf5f82',
      background: '#121212',
      surface: '#1e1e1e',
      text: '#ffffff',
      textSecondary: '#aaaaaa',
      textDisabled: '#666666',
      error: '#f44336',
      errorLight: '#e57373',
      errorDark: '#d32f2f',
      warning: '#ff9800',
      warningLight: '#ffb74d',
      warningDark: '#f57c00',
      success: '#4caf50',
      successLight: '#81c784',
      successDark: '#388e3c',
      info: '#2196f3',
      infoLight: '#64b5f6',
      infoDark: '#1976d2',
      surfaceBorder: '#333333',
      buttonPrimaryBg: '#90caf9',
      buttonPrimaryText: '#000000',
      buttonPrimaryHover: '#64b5f6',
      buttonOutlineBorder: '#90caf9',
      buttonOutlineHover: 'rgba(144, 202, 249, 0.08)',
      backgroundHover: 'rgba(255, 255, 255, 0.08)',
      inputBackground: '#1e1e1e',
      inputBorder: '#333333',
      inputBorderFocus: '#90caf9',
      inputText: '#ffffff',
      inputPlaceholder: '#666666',
      navBackground: '#1e1e1e',
      navBorder: '#333333',
      backgroundSecondary: '#2a2a2a',
      backgroundTertiary: '#333333',
    },
  },
}));

describe('muiTheme', () => {
  const mockCreateTheme = createTheme as jest.MockedFunction<typeof createTheme>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('lightTheme', () => {
    it('creates theme with light mode', () => {
      expect(lightTheme.palette.mode).toBe('light');
    });

    it('uses correct primary colors from themeConfig', () => {
      expect(lightTheme.palette.primary).toEqual({
        main: themeConfig.light.primary,
        light: themeConfig.light.primaryLight,
        dark: themeConfig.light.primaryDark,
      });
    });

    it('uses correct secondary colors from themeConfig', () => {
      expect(lightTheme.palette.secondary).toEqual({
        main: themeConfig.light.secondary,
        light: themeConfig.light.secondaryLight,
        dark: themeConfig.light.secondaryDark,
      });
    });

    it('uses correct background colors', () => {
      expect(lightTheme.palette.background).toEqual({
        default: themeConfig.light.background,
        paper: themeConfig.light.surface,
      });
    });

    it('uses correct text colors', () => {
      expect(lightTheme.palette.text).toEqual({
        primary: themeConfig.light.text,
        secondary: themeConfig.light.textSecondary,
        disabled: themeConfig.light.textDisabled,
      });
    });

    it('configures MuiButton component correctly', () => {
      expect(lightTheme.components.MuiButton.styleOverrides.root).toEqual({
        textTransform: 'none',
      });
      expect(lightTheme.components.MuiButton.styleOverrides.contained).toMatchObject({
        backgroundColor: themeConfig.light.buttonPrimaryBg,
        color: themeConfig.light.buttonPrimaryText,
      });
    });

    it('configures MuiTextField component correctly', () => {
      const textFieldOverrides = lightTheme.components.MuiTextField.styleOverrides.root;
      expect(textFieldOverrides['& .MuiOutlinedInput-root']).toMatchObject({
        backgroundColor: themeConfig.light.inputBackground,
      });
    });

    it('sets correct typography', () => {
      expect(lightTheme.typography.fontFamily).toBe('"Inter", "Roboto", "Helvetica", "Arial", sans-serif');
      expect(lightTheme.typography.h1.color).toBe(themeConfig.light.text);
      expect(lightTheme.typography.body1.color).toBe(themeConfig.light.text);
      expect(lightTheme.typography.body2.color).toBe(themeConfig.light.textSecondary);
    });

    it('configures all status colors', () => {
      expect(lightTheme.palette.error).toEqual({
        main: themeConfig.light.error,
        light: themeConfig.light.errorLight,
        dark: themeConfig.light.errorDark,
      });
      expect(lightTheme.palette.warning).toEqual({
        main: themeConfig.light.warning,
        light: themeConfig.light.warningLight,
        dark: themeConfig.light.warningDark,
      });
      expect(lightTheme.palette.success).toEqual({
        main: themeConfig.light.success,
        light: themeConfig.light.successLight,
        dark: themeConfig.light.successDark,
      });
      expect(lightTheme.palette.info).toEqual({
        main: themeConfig.light.info,
        light: themeConfig.light.infoLight,
        dark: themeConfig.light.infoDark,
      });
    });
  });

  describe('darkTheme', () => {
    it('creates theme with dark mode', () => {
      expect(darkTheme.palette.mode).toBe('dark');
    });

    it('uses correct primary colors from themeConfig', () => {
      expect(darkTheme.palette.primary).toEqual({
        main: themeConfig.dark.primary,
        light: themeConfig.dark.primaryLight,
        dark: themeConfig.dark.primaryDark,
      });
    });

    it('uses correct background colors', () => {
      expect(darkTheme.palette.background).toEqual({
        default: themeConfig.dark.background,
        paper: themeConfig.dark.surface,
      });
    });

    it('removes background images in dark mode', () => {
      expect(darkTheme.components.MuiPaper.styleOverrides.root.backgroundImage).toBe('none');
      expect(darkTheme.components.MuiCard.styleOverrides.root.backgroundImage).toBe('none');
      expect(darkTheme.components.MuiAppBar.styleOverrides.root.backgroundImage).toBe('none');
      expect(darkTheme.components.MuiDrawer.styleOverrides.paper.backgroundImage).toBe('none');
    });

    it('configures additional dark mode components', () => {
      // IconButton
      expect(darkTheme.components.MuiIconButton).toBeDefined();
      expect(darkTheme.components.MuiIconButton.styleOverrides.root.color).toBe(themeConfig.dark.text);

      // Checkbox
      expect(darkTheme.components.MuiCheckbox).toBeDefined();
      expect(darkTheme.components.MuiCheckbox.styleOverrides.root.color).toBe(themeConfig.dark.textSecondary);

      // Radio
      expect(darkTheme.components.MuiRadio).toBeDefined();
      expect(darkTheme.components.MuiRadio.styleOverrides.root.color).toBe(themeConfig.dark.textSecondary);

      // Switch
      expect(darkTheme.components.MuiSwitch).toBeDefined();
      expect(darkTheme.components.MuiSwitch.styleOverrides.root['& .MuiSwitch-track'].backgroundColor).toBe(themeConfig.dark.backgroundTertiary);

      // Progress indicators
      expect(darkTheme.components.MuiLinearProgress.styleOverrides.root.backgroundColor).toBe(themeConfig.dark.backgroundTertiary);
      expect(darkTheme.components.MuiCircularProgress.styleOverrides.root.color).toBe(themeConfig.dark.primary);
    });

    it('configures TextField with dark theme specific styles', () => {
      const textFieldOverrides = darkTheme.components.MuiTextField.styleOverrides.root;
      expect(textFieldOverrides['& .MuiInputLabel-root']).toMatchObject({
        color: themeConfig.dark.textSecondary,
      });
      expect(textFieldOverrides['& .MuiInputLabel-root']['&.Mui-focused']).toMatchObject({
        color: themeConfig.dark.primary,
      });
    });
  });

  describe('getTheme', () => {
    it('returns lightTheme for light mode', () => {
      const theme = getTheme('light');
      expect(theme).toBe(lightTheme);
    });

    it('returns darkTheme for dark mode', () => {
      const theme = getTheme('dark');
      expect(theme).toBe(darkTheme);
    });
  });

  describe('createTheme calls', () => {
    it('calls createTheme for both themes', () => {
      // The themes are created when the module is imported
      // Since we import at the top, they should already be created
      expect(mockCreateTheme).toHaveBeenCalledTimes(2);
    });

    it('passes ThemeOptions type to createTheme', () => {
      expect(mockCreateTheme).toHaveBeenCalledWith(
        expect.objectContaining({
          palette: expect.any(Object),
          components: expect.any(Object),
          typography: expect.any(Object),
        })
      );
    });
  });

  describe('component consistency', () => {
    it('has consistent component overrides between themes', () => {
      const lightComponents = Object.keys(lightTheme.components);
      const darkComponents = Object.keys(darkTheme.components);

      // Common components should exist in both themes
      const commonComponents = [
        'MuiPaper',
        'MuiCard',
        'MuiButton',
        'MuiTextField',
        'MuiAlert',
        'MuiAppBar',
        'MuiDrawer',
        'MuiDivider',
        'MuiTableCell',
        'MuiChip',
      ];

      commonComponents.forEach(component => {
        expect(lightComponents).toContain(component);
        expect(darkComponents).toContain(component);
      });
    });

    it('has consistent typography configuration', () => {
      const typographyKeys = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'body1', 'body2'];
      
      typographyKeys.forEach(key => {
        expect(lightTheme.typography[key]).toBeDefined();
        expect(darkTheme.typography[key]).toBeDefined();
      });
    });
  });
});