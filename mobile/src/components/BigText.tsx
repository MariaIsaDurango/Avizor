import { Text, StyleSheet, TextStyle } from 'react-native';
import { colors } from '../constants/colors';
import { fontSize, fontWeight } from '../constants/typography';

interface BigTextProps {
  children: React.ReactNode;
  style?: TextStyle;
}

export default function BigText({ children, style }: BigTextProps) {
  return (
    <Text style={[styles.text, style]} accessibilityRole="text">
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: fontSize.bigText,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    lineHeight: fontSize.bigText * 1.4,
  },
});
