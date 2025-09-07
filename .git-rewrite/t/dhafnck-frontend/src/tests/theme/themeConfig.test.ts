import { themeConfig, getThemeColors, cssVariables, applyThemeToRoot } from '../../theme/themeConfig';

describe('themeConfig', () => {
  describe('theme structure', () => {
    it('has light and dark theme configurations', () => {
      expect(themeConfig).toHaveProperty('light');
      expect(themeConfig).toHaveProperty('dark');
    });

    it('light theme has all required color properties', () => {
      const requiredProperties = [
        'primary', 'primaryHover', 'primaryLight', 'primaryDark',
        'secondary', 'secondaryHover', 'secondaryLight', 'secondaryDark',
        'background', 'backgroundSecondary', 'backgroundTertiary', 'backgroundHover', 'backgroundActive',
        'surface', 'surfaceHover', 'surfaceBorder', 'surfaceBorderHover',
        'text', 'textSecondary', 'textTertiary', 'textDisabled', 'textInverse',
        'inputBackground', 'inputBorder', 'inputBorderFocus', 'inputBorderError', 'inputText', 'inputPlaceholder',
        'buttonPrimaryBg', 'buttonPrimaryHover', 'buttonPrimaryText',
        'buttonSecondaryBg', 'buttonSecondaryHover', 'buttonSecondaryText',
        'buttonOutlineBorder', 'buttonOutlineHover', 'buttonDangerBg', 'buttonDangerHover',
        'success', 'successLight', 'successDark',
        'warning', 'warningLight', 'warningDark',
        'error', 'errorLight', 'errorDark',
        'info', 'infoLight', 'infoDark',
        'shadow', 'shadowMedium', 'shadowLarge', 'overlay',
        'scrollbarTrack', 'scrollbarThumb', 'scrollbarThumbHover',
        'codeBackground', 'codeBorder', 'codeText',
        'navBackground', 'navText', 'navTextHover', 'navTextActive', 'navBorder'
      ];

      requiredProperties.forEach(prop => {
        expect(themeConfig.light).toHaveProperty(prop);
      });
    });

    it('dark theme has all required color properties', () => {
      const lightKeys = Object.keys(themeConfig.light);
      const darkKeys = Object.keys(themeConfig.dark);
      
      expect(darkKeys).toEqual(lightKeys);
    });

    it('all color values are valid strings', () => {
      Object.values(themeConfig.light).forEach(value => {
        expect(typeof value).toBe('string');
        expect(value).toBeTruthy();
      });

      Object.values(themeConfig.dark).forEach(value => {
        expect(typeof value).toBe('string');
        expect(value).toBeTruthy();
      });
    });
  });

  describe('color values', () => {
    it('light theme uses appropriate light colors', () => {
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.text).toBe('#111827'); // gray-900
      expect(themeConfig.light.primary).toBe('#3b82f6'); // blue-500
    });

    it('dark theme uses appropriate dark colors', () => {
      expect(themeConfig.dark.background).toBe('#0f172a'); // slate-900
      expect(themeConfig.dark.text).toBe('#f1f5f9'); // slate-100
      expect(themeConfig.dark.primary).toBe('#60a5fa'); // blue-400
    });

    it('maintains contrast between background and text', () => {
      // Light theme: dark text on light background
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.text).toBe('#111827');

      // Dark theme: light text on dark background
      expect(themeConfig.dark.background).toBe('#0f172a');
      expect(themeConfig.dark.text).toBe('#f1f5f9');
    });
  });

  describe('getThemeColors', () => {
    it('returns light theme colors when isDark is false', () => {
      const colors = getThemeColors(false);
      expect(colors).toBe(themeConfig.light);
    });

    it('returns dark theme colors when isDark is true', () => {
      const colors = getThemeColors(true);
      expect(colors).toBe(themeConfig.dark);
    });
  });

  describe('cssVariables', () => {
    it('maps CSS variables to theme properties', () => {
      expect(cssVariables['--color-primary']).toBe('primary');
      expect(cssVariables['--color-background']).toBe('background');
      expect(cssVariables['--color-text']).toBe('text');
    });

    it('has CSS variables for all major color categories', () => {
      const variableKeys = Object.keys(cssVariables);
      
      // Check primary colors
      expect(variableKeys).toContain('--color-primary');
      expect(variableKeys).toContain('--color-primary-hover');
      expect(variableKeys).toContain('--color-primary-light');
      expect(variableKeys).toContain('--color-primary-dark');

      // Check background colors
      expect(variableKeys).toContain('--color-background');
      expect(variableKeys).toContain('--color-background-secondary');
      expect(variableKeys).toContain('--color-background-tertiary');

      // Check text colors
      expect(variableKeys).toContain('--color-text');
      expect(variableKeys).toContain('--color-text-secondary');
      expect(variableKeys).toContain('--color-text-tertiary');

      // Check status colors
      expect(variableKeys).toContain('--color-success');
      expect(variableKeys).toContain('--color-warning');
      expect(variableKeys).toContain('--color-error');
      expect(variableKeys).toContain('--color-info');
    });

    it('all CSS variable values correspond to valid theme properties', () => {
      const lightThemeKeys = Object.keys(themeConfig.light);
      
      Object.values(cssVariables).forEach(themeKey => {
        expect(lightThemeKeys).toContain(themeKey);
      });
    });
  });

  describe('applyThemeToRoot', () => {
    let mockSetProperty: jest.Mock;
    let originalDocumentElement: HTMLElement;

    beforeEach(() => {
      mockSetProperty = jest.fn();
      originalDocumentElement = document.documentElement;
      
      // Mock document.documentElement.style.setProperty
      Object.defineProperty(document, 'documentElement', {
        value: {
          style: {
            setProperty: mockSetProperty
          }
        },
        writable: true,
        configurable: true
      });
    });

    afterEach(() => {
      document.documentElement = originalDocumentElement;
    });

    it('applies light theme CSS variables to root', () => {
      applyThemeToRoot(false);

      expect(mockSetProperty).toHaveBeenCalledWith('--color-primary', themeConfig.light.primary);
      expect(mockSetProperty).toHaveBeenCalledWith('--color-background', themeConfig.light.background);
      expect(mockSetProperty).toHaveBeenCalledWith('--color-text', themeConfig.light.text);
    });

    it('applies dark theme CSS variables to root', () => {
      applyThemeToRoot(true);

      expect(mockSetProperty).toHaveBeenCalledWith('--color-primary', themeConfig.dark.primary);
      expect(mockSetProperty).toHaveBeenCalledWith('--color-background', themeConfig.dark.background);
      expect(mockSetProperty).toHaveBeenCalledWith('--color-text', themeConfig.dark.text);
    });

    it('sets all CSS variables defined in cssVariables', () => {
      applyThemeToRoot(false);

      const expectedCallCount = Object.keys(cssVariables).length;
      expect(mockSetProperty).toHaveBeenCalledTimes(expectedCallCount);
    });

    it('correctly maps CSS variable names to theme values', () => {
      applyThemeToRoot(true);

      Object.entries(cssVariables).forEach(([cssVar, themeKey]) => {
        expect(mockSetProperty).toHaveBeenCalledWith(
          cssVar,
          themeConfig.dark[themeKey as keyof typeof themeConfig.dark]
        );
      });
    });
  });

  describe('theme consistency', () => {
    it('button colors match primary colors', () => {
      // Light theme
      expect(themeConfig.light.buttonPrimaryBg).toBe(themeConfig.light.primary);
      expect(themeConfig.light.buttonPrimaryHover).toBe(themeConfig.light.primaryHover);

      // Dark theme
      expect(themeConfig.dark.buttonPrimaryBg).toBe('#3b82f6'); // Specific blue for dark theme
    });

    it('info colors relate to primary colors', () => {
      // Light theme: info should be similar to primary
      expect(themeConfig.light.info).toBe(themeConfig.light.primary);
      expect(themeConfig.light.infoLight).toBe(themeConfig.light.primaryLight);
      expect(themeConfig.light.infoDark).toBe(themeConfig.light.primaryHover);
    });

    it('maintains color hierarchy in backgrounds', () => {
      // Light theme: background colors get progressively darker
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.backgroundSecondary).toBe('#f9fafb'); // gray-50
      expect(themeConfig.light.backgroundTertiary).toBe('#f3f4f6'); // gray-100

      // Dark theme: background colors get progressively lighter
      expect(themeConfig.dark.background).toBe('#0f172a'); // slate-900
      expect(themeConfig.dark.backgroundSecondary).toBe('#1e293b'); // slate-800
      expect(themeConfig.dark.backgroundTertiary).toBe('#334155'); // slate-700
    });
  });
});