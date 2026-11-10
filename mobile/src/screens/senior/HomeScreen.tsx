import { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import BigText from '../../components/BigText';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { submitAnalysis, InputType, Verdict, BlockTemplate } from '../../services/analyses';

const TABS: { key: InputType; label: string }[] = [
  { key: 'text', label: 'Texto' },
  { key: 'url', label: 'Enlace' },
  { key: 'phone_number', label: 'Teléfono' },
];

const BLOCK_TEMPLATE_MESSAGES: Record<BlockTemplate, string> = {
  FAKE_DO_NOT_TOUCH: 'No lo toques',
  DANGEROUS_LINK: 'Enlace peligroso',
  SUSPICIOUS_CALL: 'Llamada sospechosa',
  ASKS_BANK_DETAILS: 'Pide datos bancarios',
  LOOKS_SAFE: 'Parece seguro',
  UNSURE_CALL_FAMILY: 'Consulta con un familiar',
};

const RISK_ICONS: Record<string, keyof typeof MaterialIcons.glyphMap> = {
  green: 'check-circle',
  amber: 'warning',
  red: 'dangerous',
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
  if (verdict.block_template) return BLOCK_TEMPLATE_MESSAGES[verdict.block_template];
  return RISK_MESSAGES[verdict.risk_level];
}

export default function SeniorHomeScreen() {
  const [inputType, setInputType] = useState<InputType>('text');
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID)
      .then(setDeviceId)
      .catch(() => setDeviceId(null));
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
    if (!deviceId) {
      setError('Tu dispositivo no está vinculado. Pide a tu Tutor el código de vinculación.');
      return;
    }
    setLoading(true);
    setError(null);
    setVerdict(null);
    try {
      const result = await submitAnalysis(deviceId, inputType, value.trim());
      setVerdict(result);
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
            accessibilityLabel={`Nivel de riesgo: ${verdict.risk_level}`}
          />
          <BigText style={{ textAlign: 'center', color: accentColor }}>
            {verdictMessage(verdict)}
          </BigText>
        </View>
        <View style={styles.footer}>
          <Button label="Analizar otro mensaje" onPress={handleReset} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen style={styles.screen}>
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
              style={[styles.tab, inputType === tab.key && styles.tabActive]}
            >
              <Text style={[styles.tabLabel, inputType === tab.key && styles.tabLabelActive]}>
                {tab.label}
              </Text>
            </Pressable>
          ))}
        </View>

        <TextInput
          style={[styles.input, inputType === 'text' && styles.inputMultiline]}
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
        />

        {inputType !== 'phone_number' && (
          <Text style={styles.disclaimer}>
            No incluyas tu nombre, DNI, número de cuenta ni otros datos personales.
          </Text>
        )}

        {error !== null && <Text style={styles.error}>{error}</Text>}
      </View>

      <View style={styles.footer}>
        {loading
          ? <ActivityIndicator size="large" color={colors.primary} />
          : (
            <Button
              label="Analizar"
              variant="action"
              disabled={!value.trim()}
              onPress={handleAnalyze}
            />
          )
        }
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    justifyContent: 'space-between',
    paddingBottom: 40,
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
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabLabel: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
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
  disclaimer: {
    fontSize: 14,
    color: colors.primary,
    opacity: 0.6,
    textAlign: 'center',
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
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
});
