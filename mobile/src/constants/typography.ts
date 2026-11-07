import { TextStyle } from 'react-native';

export const fontSize = {
  body: 18,
  button: 24,
  heading: 28,
  bigText: 36,
} as const;

export const fontWeight = {
  regular: '400' as TextStyle['fontWeight'],
  bold: '700' as TextStyle['fontWeight'],
} as const;
