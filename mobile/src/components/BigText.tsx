import { Text, StyleSheet, TextStyle } from 'react-native';
import { colors } from '../constants/colors';
import { fontSize, fontWeight } from '../constants/typography';
import { useAccessibility } from '../contexts/AccessibilityContext';

interface BigTextProps {
  children: React.ReactNode;
  style?: TextStyle;
}

export default function BigText({ children, style }: BigTextProps) {
  const { largeText } = useAccessibility();
  const size = largeText ? fontSize.bigText * 1.4 : fontSize.bigText;
  return (
    <Text style={[styles.text, { fontSize: size, lineHeight: size * 1.4 }, style]} accessibilityRole="text">
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: {
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
});
