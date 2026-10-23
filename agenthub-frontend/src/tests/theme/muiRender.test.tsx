import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import { ThemeProvider } from '@mui/material/styles';
import { darkTheme, lightTheme } from '../../theme/muiTheme';

// The arm createTheme cannot pass. MUI accepts a `var()` palette value at build
// and throws when a component runs colour maths on it at render, which unmounts
// the tree because src has no error boundary. Alert, Button, Checkbox, Divider,
// IconButton and a TextField with an adornment are the six that throw, five of
// them on LoginForm - so this is the shipped surface, not a hypothetical one.
const THEMES = [
  { mode: 'light', theme: lightTheme },
  { mode: 'dark', theme: darkTheme },
] as const;

const SURFACE = (
  <>
    <Button variant="text">text</Button>
    <Button variant="outlined">outlined</Button>
    <Button variant="contained">contained</Button>
    <Checkbox defaultChecked />
    <FormControlLabel control={<Checkbox />} label="remember" />
    <Divider />
    <IconButton aria-label="reveal">*</IconButton>
    <TextField
      label="password"
      defaultValue=""
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton aria-label="show">x</IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
    <Alert severity="error">sign-in failed</Alert>
  </>
);

describe('the palette renders', () => {
  THEMES.forEach(({ mode, theme }) => {
    it(`${mode}: every colour-maths component renders without throwing`, () => {
      expect(() => render(<ThemeProvider theme={theme}>{SURFACE}</ThemeProvider>)).not.toThrow();
      expect(screen.getByRole('button', { name: 'contained' })).toBeInTheDocument();
      expect(screen.getByRole('alert')).toHaveTextContent('sign-in failed');
      expect(screen.getByLabelText('password')).toBeInTheDocument();
    });
  });
});
