import { View, Text, Pressable, StyleSheet, Linking } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import { RootStackParamList } from '../../navigation/types';
import { BlockTemplate } from '../../services/analyses';
import { colors } from '../../constants/colors';
import { fontWeight } from '../../constants/typography';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorBlock'>;

type Config = {
  message: string;
  empathy: string;
  icon: keyof typeof MaterialIcons.glyphMap;
  background: string;
  riskLabel: string;
};

const CONFIGS: Record<BlockTemplate, Config> = {
  FAKE_DO_NOT_TOUCH: {
    message: '¡Cuidado! Este mensaje es falso.\nNo toques nada.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  DANGEROUS_LINK: {
    message: 'Este enlace es peligroso.\nNo lo abras.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  SUSPICIOUS_CALL: {
    message: 'Esta llamada puede ser una estafa.\nDesconfía.',
    empathy: 'No respondas. Estás protegido/a.',
    icon: 'warning',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  ASKS_BANK_DETAILS: {
    message: 'Nunca des tus datos bancarios.\nEsto es un fraude.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  LOOKS_SAFE: {
    message: 'Este mensaje parece seguro.',
    empathy: '¡Todo bien! No hay nada de qué preocuparse.',
    icon: 'check-circle',
    background: colors.success,
    riskLabel: 'SEGURO',
  },
  UNSURE_CALL_FAMILY: {
    message: 'No estamos seguros.\nConsulta con tu familiar\nantes de hacer nada.',
    empathy: 'Es mejor preguntar cuando hay dudas.',
    icon: 'warning',
    background: colors.warning,
    riskLabel: 'ATENCIÓN',
  },
};

export default function SeniorBlockScreen({ navigation, route }: Props) {
  const config = CONFIGS[route.params.template];
  const { largeText, colorBlind } = useAccessibility();

  return (
    <Screen style={{ backgroundColor: config.background }}>
      <View style={styles.content}>
        <MaterialIcons
          name={config.icon}
          size={96}
          color={colors.white}
          importantForAccessibility="no-hide-descendants"
          accessibilityElementsHidden
        />
        {colorBlind && (
          <Text style={[styles.riskLabel, largeText && styles.riskLabelLarge]}>
            {config.riskLabel}
          </Text>
        )}
        <Text style={[styles.message, largeText && styles.messageLarge]}>{config.message}</Text>
        <Text style={[styles.empathy, largeText && styles.empathyLarge]}>{config.empathy}</Text>
      </View>

      <View style={styles.footer}>
        <Pressable
          style={[styles.callButton, largeText && styles.callButtonLarge]}
          onPress={() => Linking.openURL('tel:')}
          accessibilityRole="button"
          accessibilityLabel="Llamar a tu familiar"
        >
          <MaterialIcons name="phone" size={largeText ? 36 : 28} color={colors.success} />
          <Text style={[styles.callLabel, largeText && styles.callLabelLarge]}>Llamar a tu familiar</Text>
        </Pressable>

        <Pressable
          style={[styles.dismissButton, largeText && styles.dismissButtonLarge]}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Estoy protegido/a, gracias"
        >
          <Text style={[styles.dismissLabel, largeText && styles.dismissLabelLarge]}>Estoy protegido/a, gracias</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flexShrink: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 24,
    paddingVertical: 24,
  },
  riskLabel: {
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 4,
    color: colors.white,
    textAlign: 'center',
    opacity: 0.85,
    borderWidth: 2,
    borderColor: colors.white,
    borderRadius: 6,
    paddingHorizontal: 16,
    paddingVertical: 4,
  },
  riskLabelLarge: {
    fontSize: 26,
  },
  message: {
    fontSize: 28,
    fontWeight: fontWeight.bold,
    color: colors.white,
    textAlign: 'center',
    lineHeight: 38,
  },
  messageLarge: {
    fontSize: 36,
    lineHeight: 48,
  },
  empathy: {
    fontSize: 20,
    fontWeight: fontWeight.bold,
    color: colors.white,
    textAlign: 'center',
    lineHeight: 28,
  },
  empathyLarge: {
    fontSize: 26,
    lineHeight: 36,
  },
  footer: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 20,
    gap: 12,
    marginBottom: 8,
  },
  callButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: '#E8F5E9',
    borderRadius: 12,
    paddingVertical: 18,
    paddingHorizontal: 20,
  },
  callButtonLarge: {
    paddingVertical: 24,
  },
  callLabel: {
    fontSize: 22,
    fontWeight: fontWeight.bold,
    color: colors.success,
  },
  callLabelLarge: {
    fontSize: 28,
  },
  dismissButton: {
    alignItems: 'center',
    paddingVertical: 14,
  },
  dismissButtonLarge: {
    paddingVertical: 18,
  },
  dismissLabel: {
    fontSize: 18,
    color: colors.primary,
    opacity: 0.7,
  },
  dismissLabelLarge: {
    fontSize: 22,
  },
});
