import { Pressable, Text, StyleSheet, ViewStyle } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { colors } from '../constants/colors';
import { fontSize, fontWeight } from '../constants/typography';

export type ButtonVariant = 'primary' | 'alert' | 'action';

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof MaterialIcons.glyphMap;
  disabled?: boolean;
  style?: ViewStyle;
}

const DEFAULT_ICONS: Partial<Record<ButtonVariant, keyof typeof MaterialIcons.glyphMap>> = {
  alert: 'warning',
  action: 'check-circle',
};

const LABEL_COLOR: Record<ButtonVariant, string> = {
  primary: colors.primary,
  alert: colors.white,
  action: colors.white,
};

export default function Button({
  label,
  onPress,
  variant = 'primary',
  icon,
  disabled = false,
  style,
}: ButtonProps) {
  const resolvedIcon = icon ?? DEFAULT_ICONS[variant];
  const showIcon = variant === 'alert' || variant === 'action';

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.base,
        variant === 'primary' && styles.primary,
        variant === 'alert' && styles.alert,
        variant === 'action' && styles.action,
        disabled && styles.disabled,
        pressed && styles.pressed,
        style,
      ]}
    >
      {showIcon && resolvedIcon && (
        <MaterialIcons
          name={resolvedIcon}
          size={28}
          color={LABEL_COLOR[variant]}
          style={styles.icon}
        />
      )}
      <Text style={[styles.label, { color: LABEL_COLOR[variant] }]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    minHeight: 56,
  },
  primary: {
    backgroundColor: colors.action,
    borderWidth: 2,
    borderColor: colors.primary,
  },
  alert: {
    backgroundColor: colors.alert,
  },
  action: {
    backgroundColor: colors.success,
  },
  disabled: {
    opacity: 0.4,
  },
  pressed: {
    opacity: 0.8,
  },
  icon: {
    marginRight: 8,
  },
  label: {
    fontSize: fontSize.button,
    fontWeight: fontWeight.bold,
  },
});
