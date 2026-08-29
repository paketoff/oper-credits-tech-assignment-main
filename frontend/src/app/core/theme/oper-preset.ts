import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

/**
 * The entire visual language of the four PrimeNG components this app uses —
 * stepper, fileupload, inputnumber, select (`UI-036`). Component styles are
 * never overridden with a CSS class; if something looks wrong, the token here
 * is wrong (`UI-039`, `2-architecture.md` ARC-037).
 *
 * One of the two legal hex surfaces (`UI-030`): the preset's palette has to be
 * literal colour values, and `make lint`'s hex grep excludes this directory
 * for exactly that reason.
 */
export const OperPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#E3EFEE',
      100: '#C7DFDD',
      200: '#9BC5C2',
      300: '#6FABA7',
      400: '#43918C',
      500: '#0B5D5B',
      600: '#084745',
      700: '#063A38',
      800: '#052D2C',
      900: '#032120',
      950: '#021413',
    },
    formField: {
      paddingX: '0.75rem',
      paddingY: '0.625rem',
      borderRadius: '6px',
      focusRing: { width: '2px', style: 'solid', color: '{primary.500}', offset: '1px' },
    },
    content: { borderRadius: '8px' },
    transitionDuration: '120ms',
  },
});
