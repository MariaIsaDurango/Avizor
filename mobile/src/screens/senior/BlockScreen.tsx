import { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, Linking, Animated, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';
import * as Haptics from 'expo-haptics';
import Screen from '../../components/Screen';
import { RootStackParamList } from '../../navigation/types';
import { BlockTemplate } from '../../services/analyses';
import { colors } from '../../constants/colors';
import { fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { reportPhoneIndicator } from '../../services/indicators';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorBlock'>;

type Config = {
  message: string;
  empathy: string;
  tip: string | null;
  icon: keyof typeof MaterialIcons.glyphMap;
  background: string;
  riskLabel: string;
};

const CONFIGS: Record<BlockTemplate, Config> = {
  FAKE_DO_NOT_TOUCH: {
    message: '¡Cuidado! Este mensaje es falso.\nNo toques nada.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    tip: '1. No pulses ningún enlace ni botón del mensaje.\n2. Cierra la app o el correo sin responder.\n3. Comenta a tu familiar lo que has recibido.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  DANGEROUS_LINK: {
    message: 'Este enlace es peligroso.\nNo lo abras.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    tip: '1. No abras el enlace.\n2. Si ya lo abriste, no escribas ningún dato.\n3. Cuéntaselo a tu familiar.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  SUSPICIOUS_CALL: {
    message: 'Esta llamada puede ser una estafa.\nDesconfía.',
    empathy: 'No respondas. Estás protegido/a.',
    tip: '1. Si sigues en la llamada, cuelga sin dar ningún dato.\n2. No devuelvas la llamada a ese número.\n3. Avisa a tu familiar, juntos podéis verificar si era real.',
    icon: 'warning',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  ASKS_BANK_DETAILS: {
    message: 'Nunca des tus datos bancarios.\nEsto es un fraude.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    tip: '1. No des ningún dato por teléfono ni por mensaje.\n2. Llama a tu banco usando el número del reverso de tu tarjeta.\n3. Avisa a tu familiar.',
    icon: 'dangerous',
    background: colors.alert,
    riskLabel: 'PELIGRO',
  },
  LOOKS_SAFE: {
    message: 'Este mensaje parece seguro.',
    empathy: '¡Todo bien! No hay nada de qué preocuparse.',
    tip: null,
    icon: 'check-circle',
    background: colors.success,
    riskLabel: 'SEGURO',
  },
  UNSURE_CALL_FAMILY: {
    message: 'No estamos seguros.\nConsulta con tu familiar\nantes de hacer nada.',
    empathy: 'Es mejor preguntar cuando hay dudas.',
    tip: '1. No respondas ni hagas clic en nada todavía.\n2. Enséñale el mensaje a tu familiar.\n3. Entre los dos podéis decidir con calma qué hacer.',
    icon: 'warning',
    background: colors.warning,
    riskLabel: 'ATENCIÓN',
  },
};

const CONFIGS_SOLO: Record<BlockTemplate, Config> = {
  FAKE_DO_NOT_TOUCH: {
    ...CONFIGS.FAKE_DO_NOT_TOUCH,
    tip: '1. No pulses ningún enlace ni botón del mensaje.\n2. Cierra la app o el correo sin responder.\n3. Si tienes dudas, contacta con la entidad a través de sus canales oficiales.',
  },
  DANGEROUS_LINK: {
    ...CONFIGS.DANGEROUS_LINK,
    tip: '1. No abras el enlace.\n2. Si ya lo abriste, no escribas ningún dato.\n3. Busca el contacto oficial de la entidad para verificar.',
  },
  SUSPICIOUS_CALL: {
    ...CONFIGS.SUSPICIOUS_CALL,
    tip: '1. Si sigues en la llamada, cuelga sin dar ningún dato.\n2. No devuelvas la llamada a ese número.\n3. Llama al número oficial de la entidad para verificar.',
  },
  ASKS_BANK_DETAILS: {
    ...CONFIGS.ASKS_BANK_DETAILS,
    tip: '1. No des ningún dato por teléfono ni por mensaje.\n2. Llama a tu banco usando el número del reverso de tu tarjeta.\n3. No respondas a este mensaje bajo ningún concepto.',
  },
  LOOKS_SAFE: CONFIGS.LOOKS_SAFE,
  UNSURE_CALL_FAMILY: {
    message: 'No estamos seguros.\nNo respondas todavía.\nVerifica antes de actuar.',
    empathy: 'Es mejor comprobar antes de hacer nada.',
    tip: '1. No respondas ni hagas clic en nada todavía.\n2. Busca el número oficial de la entidad.\n3. Llama para verificar si el mensaje es real.',
    icon: 'warning',
    background: colors.warning,
    riskLabel: 'ATENCIÓN',
  },
};

export default function SeniorBlockScreen({ navigation, route }: Props) {
  const { largeText, colorBlind, hardOfHearing } = useAccessibility();
  const [pulseAnim] = useState(() => new Animated.Value(1));
  const [guardianPhone, setGuardianPhone] = useState<string | null>(null);
  const [isSeniorSolo, setIsSeniorSolo] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [reporting, setReporting] = useState(false);
  const [reported, setReported] = useState(false);
  const [reportError, setReportError] = useState(false);
  const { phoneNumber } = route.params;

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEYS.GUARDIAN_PHONE)
      .then(setGuardianPhone)
      .catch(() => {});
    SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE)
      .then(mode => setIsSeniorSolo(mode === 'senior_solo'))
      .catch(() => {});
    SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID)
      .then(setDeviceId)
      .catch(() => {});
  }, []);

  async function handleReport() {
    if (!phoneNumber || reported || reporting) return;
    setReportError(false);
    setReporting(true);
    try {
      await reportPhoneIndicator(deviceId, phoneNumber);
      setReported(true);
      if (hardOfHearing) {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      }
    } catch {
      setReportError(true);
    } finally {
      setReporting(false);
    }
  }

  const config = (isSeniorSolo ? CONFIGS_SOLO : CONFIGS)[route.params.template];

  useEffect(() => {
    if (!hardOfHearing) return;

    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});

    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.25, duration: 350, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 350, useNativeDriver: true }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [hardOfHearing, pulseAnim]);

  return (
    <Screen style={{ backgroundColor: config.background }}>
      <View style={styles.content}>
        <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
          <MaterialIcons
            name={config.icon}
            size={96}
            color={colors.white}
            importantForAccessibility="no-hide-descendants"
            accessibilityElementsHidden
          />
        </Animated.View>
        {colorBlind && (
          <Text style={[styles.riskLabel, largeText && styles.riskLabelLarge]}>
            {config.riskLabel}
          </Text>
        )}
        <Text style={[styles.message, largeText && styles.messageLarge]}>{config.message}</Text>
        <Text style={[styles.empathy, largeText && styles.empathyLarge]}>{config.empathy}</Text>
        {config.tip && (
          <View style={styles.tipBox}>
            <MaterialIcons name="lightbulb" size={18} color={colors.white} style={{ opacity: 0.9 }} />
            <Text style={[styles.tip, largeText && styles.tipLarge]}>{config.tip}</Text>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        {guardianPhone !== null && (
          <Pressable
            style={[styles.callButton, largeText && styles.callButtonLarge]}
            onPress={() => Linking.openURL(`tel:${guardianPhone}`)}
            accessibilityRole="button"
            accessibilityLabel="Llamar a tu familiar"
          >
            <MaterialIcons name="phone" size={largeText ? 36 : 28} color={colors.success} />
            <Text style={[styles.callLabel, largeText && styles.callLabelLarge]}>Llamar a tu familiar</Text>
          </Pressable>
        )}

        {phoneNumber && (
          reporting
            ? <ActivityIndicator size="large" color={colors.primary} accessibilityLabel="Reportando número, por favor espera" />
            : (
              <>
                <Pressable
                  style={[styles.reportButton, largeText && styles.reportButtonLarge]}
                  onPress={reported ? () => navigation.goBack() : handleReport}
                  accessibilityRole="button"
                  accessibilityLabel={reported ? 'Número reportado. Pulsa para cerrar' : 'Reportar este número como spam'}
                >
                  <MaterialIcons name={reported ? 'check' : 'flag'} size={largeText ? 26 : 20} color={colors.white} accessibilityElementsHidden importantForAccessibility="no-hide-descendants" />
                  <Text style={[styles.reportLabel, largeText && styles.reportLabelLarge]}>
                    {reported ? 'Aceptar' : 'Reportar número'}
                  </Text>
                </Pressable>
                {reportError && (
                  <Text style={[styles.reportErrorText, largeText && styles.reportErrorTextLarge]} accessibilityLiveRegion="assertive">
                    No se pudo reportar el número. Inténtalo de nuevo.
                  </Text>
                )}
              </>
            )
        )}

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
  tipBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginTop: 4,
  },
  tip: {
    flex: 1,
    fontSize: 16,
    color: colors.white,
    opacity: 0.9,
    lineHeight: 22,
  },
  tipLarge: { fontSize: 20, lineHeight: 28 },
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
  reportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: colors.alert,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  reportButtonLarge: {
    paddingVertical: 20,
  },
  reportLabel: {
    fontSize: 18,
    fontWeight: fontWeight.bold,
    color: colors.white,
  },
  reportLabelLarge: {
    fontSize: 24,
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
  reportErrorText: {
    fontSize: 14,
    color: colors.alert,
    textAlign: 'center',
    marginTop: 4,
  },
  reportErrorTextLarge: { fontSize: 18 },
});
