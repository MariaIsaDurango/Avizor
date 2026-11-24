import { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  TouchableWithoutFeedback,
  Keyboard,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import * as SecureStore from 'expo-secure-store';
import { MaterialIcons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import BigText from '../../components/BigText';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { submitAnalysis, InputType, Verdict } from '../../services/analyses';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { RootStackParamList } from '../../navigation/types';

const TABS: { key: InputType; label: string }[] = [
  { key: 'text', label: 'Texto' },
  { key: 'url', label: 'Enlace' },
  { key: 'phone_number', label: 'Teléfono' },
];

const RISK_ICONS: Record<string, keyof typeof MaterialIcons.glyphMap> = {
  green: 'check-circle',
  amber: 'warning',
  red: 'dangerous',
};

const RISK_ACCESSIBILITY: Record<string, string> = {
  green: 'seguro',
  amber: 'sospechoso',
  red: 'peligro',
};

const RISK_COLORS: Record<string, string> = {
  green: colors.success,
  amber: colors.warning,
  red: colors.alert,
};

const RISK_MESSAGES: Record<string, string> = {
  green: 'Parece seguro',
  amber: 'Podría ser sospechoso',
  red: '¡Peligro! No lo abras',
};

function verdictMessage(verdict: Verdict): string {
  return RISK_MESSAGES[verdict.risk_level];
}

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorHome'>;

export default function SeniorHomeScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const [inputType, setInputType] = useState<InputType>('text');
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [isSeniorSolo, setIsSeniorSolo] = useState(false);
  const { largeText, colorBlind, hardOfHearing } = useAccessibility();

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID)
      .then(setDeviceId)
      .catch(() => setDeviceId(null));
    SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE)
      .then(mode => setIsSeniorSolo(mode === 'senior_solo'))
      .catch(() => {});
  }, []);

  function handleTabChange(tab: InputType) {
    setInputType(tab);
    setValue('');
    setError(null);
    setVerdict(null);
  }

  async function handleAnalyze() {
    if (!value.trim()) {
      setError('Introduce el contenido a analizar.');
      return;
    }
    if (!deviceId && !isSeniorSolo) {
      setError('Tu dispositivo no está vinculado. Pide a tu Tutor el código de vinculación.');
      return;
    }
    setLoading(true);
    setError(null);
    setVerdict(null);
    try {
      const result = await submitAnalysis(deviceId, inputType, value.trim());
      if (result.block_template) {
        if (hardOfHearing) {
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
        }
        handleReset();
        navigation.navigate('SeniorBlock', { template: result.block_template });
      } else {
        if (hardOfHearing) {
          const feedbackType = result.risk_level === 'green'
            ? Haptics.NotificationFeedbackType.Success
            : result.risk_level === 'red'
            ? Haptics.NotificationFeedbackType.Error
            : Haptics.NotificationFeedbackType.Warning;
          await Haptics.notificationAsync(feedbackType).catch(() => {});
        }
        setVerdict(result);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al analizar el contenido.');
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setValue('');
    setVerdict(null);
    setError(null);
  }

if (verdict) {
    const accentColor = RISK_COLORS[verdict.risk_level];
    return (
      <Screen style={styles.screen}>
        <View style={[styles.verdictCard, { borderColor: accentColor }]}>
          <MaterialIcons
            name={RISK_ICONS[verdict.risk_level]}
            size={64}
            color={accentColor}
            accessibilityLabel={`Nivel de riesgo: ${RISK_ACCESSIBILITY[verdict.risk_level]}`}
          />
          {colorBlind && (
            <Text style={[styles.verdictLabel, { color: accentColor }]}>
              {RISK_ACCESSIBILITY[verdict.risk_level].toUpperCase()}
            </Text>
          )}
          <BigText style={{ textAlign: 'center', color: accentColor }}>
            {verdictMessage(verdict)}
          </BigText>
        </View>
        <View style={styles.footer}>
          <Button label="Analizar otro mensaje" large={largeText} onPress={handleReset} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen style={styles.screen}>
      <Pressable
        style={[styles.settingsBtn, { top: insets.top + 8 }]}
        onPress={() => navigation.navigate('SeniorSettings')}
        accessibilityRole="button"
        accessibilityLabel="Ajustes"
      >
        <MaterialIcons name="settings" size={22} color={colors.primary} style={{ opacity: 0.4 }} />
      </Pressable>

      <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
        <View style={styles.inner}>
          <View style={styles.top}>
            <BigText style={styles.title}>Avizor</BigText>
            <Text style={styles.subtitle}>¿Has recibido algo sospechoso?</Text>
          </View>

          <View style={styles.middle}>
            <View style={styles.tabs} accessibilityRole="tablist">
              {TABS.map((tab) => (
                <Pressable
                  key={tab.key}
                  onPress={() => handleTabChange(tab.key)}
                  accessibilityRole="tab"
                  accessibilityState={{ selected: inputType === tab.key }}
                  style={[styles.tab, largeText && styles.tabLarge, inputType === tab.key && styles.tabActive]}
                >
                  <Text style={[styles.tabLabel, largeText && styles.tabLabelLarge, inputType === tab.key && styles.tabLabelActive]}>
                    {tab.label}
                  </Text>
                </Pressable>
              ))}
            </View>

            <TextInput
              style={[
                styles.input,
                inputType === 'text' && styles.inputMultiline,
                largeText && styles.inputLarge,
              ]}
              placeholder={
                inputType === 'text'
                  ? 'Pega aquí el mensaje sospechoso'
                  : inputType === 'url'
                  ? 'Pega aquí el enlace sospechoso'
                  : 'Número en formato +34 600 000 000'
              }
              placeholderTextColor={colors.primary}
              value={value}
              onChangeText={(v) => { setValue(v); setError(null); }}
              multiline={inputType === 'text'}
              numberOfLines={inputType === 'text' ? 5 : 1}
              keyboardType={inputType === 'phone_number' ? 'phone-pad' : 'default'}
              autoCapitalize="none"
              autoCorrect={false}
              accessibilityLabel={
                inputType === 'text'
                  ? 'Campo de texto del mensaje'
                  : inputType === 'url'
                  ? 'Campo del enlace'
                  : 'Campo del número de teléfono'
              }
              accessibilityHint="Escribe o pega el contenido que quieres analizar y luego pulsa Analizar"
            />

            {inputType !== 'phone_number' && (
              <Text style={[styles.disclaimer, largeText && styles.disclaimerLarge]}>
                No incluyas tu nombre, DNI, número de cuenta ni otros datos personales.
              </Text>
            )}

            {error !== null && (
              <Text style={[styles.error, largeText && styles.errorLarge]}>{error}</Text>
            )}
          </View>

          <View style={styles.footer}>
            {loading
              ? <ActivityIndicator size="large" color={colors.primary} />
              : (
                <Button
                  label="Analizar"
                  variant="action"
                  disabled={!value.trim()}
                  large={largeText}
                  onPress={handleAnalyze}
                />
              )
            }
          </View>
        </View>
      </TouchableWithoutFeedback>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingBottom: 40,
  },
  inner: {
    flex: 1,
    justifyContent: 'space-between',
  },
  top: {
    alignItems: 'center',
    marginTop: 32,
    gap: 8,
  },
  title: {
    color: colors.primary,
  },
  subtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.7,
    textAlign: 'center',
  },
  middle: {
    gap: 16,
  },
  tabs: {
    flexDirection: 'row',
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: colors.primary,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: colors.white,
  },
  tabLarge: {
    paddingVertical: 18,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabLabel: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  tabLabelLarge: {
    fontSize: 22,
  },
  tabLabelActive: {
    color: colors.white,
  },
  input: {
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 8,
    padding: 14,
    fontSize: fontSize.body,
    color: colors.primary,
    backgroundColor: colors.white,
  },
  inputMultiline: {
    minHeight: 120,
    textAlignVertical: 'top',
  },
  inputLarge: {
    fontSize: 20,
    minHeight: 140,
  },
  disclaimer: {
    fontSize: 14,
    color: colors.primary,
    opacity: 0.6,
    textAlign: 'center',
  },
  disclaimerLarge: {
    fontSize: 18,
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
  },
  errorLarge: {
    fontSize: 22,
  },
  footer: {
    gap: 12,
  },
  verdictCard: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
    borderWidth: 3,
    borderRadius: 16,
    marginVertical: 32,
    padding: 32,
  },
  verdictMessage: {
    textAlign: 'center',
  },
  verdictLabel: {
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: 3,
    textAlign: 'center',
  },
  settingsBtn: {
    position: 'absolute',
    right: 16,
    padding: 8,
    zIndex: 1,
  },
});
