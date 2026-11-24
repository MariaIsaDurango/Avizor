import { useState, useEffect } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import * as Haptics from 'expo-haptics';
import * as SecureStore from 'expo-secure-store';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { submitAnalysis, Verdict } from '../../services/analyses';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorShareEmail'>;

const RISK_LABEL: Record<string, string> = {
  green: 'Sin señales de riesgo',
  amber: 'Sospechoso',
  red: 'Peligroso — no hagas clic',
};

const RISK_COLOR: Record<string, string> = {
  green: colors.success,
  amber: colors.warning,
  red: colors.alert,
};


export default function ShareEmailScreen({ route, navigation }: Props) {
  const { text } = route.params;
  const { hardOfHearing } = useAccessibility();
  const [loading, setLoading] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [error, setError] = useState('');
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [isSeniorSolo, setIsSeniorSolo] = useState(false);

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID).then(setDeviceId).catch(() => {});
    SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE)
      .then(mode => setIsSeniorSolo(mode === 'senior_solo'))
      .catch(() => {});
  }, []);

  async function handleAnalyze() {
    setLoading(true);
    setError('');
    try {
      if (!deviceId && !isSeniorSolo) throw new Error('Dispositivo no vinculado.');
      const result = await submitAnalysis(deviceId, 'text', text.slice(0, 5000));
      if (hardOfHearing) {
        await Haptics.notificationAsync(
          result.risk_level === 'red'
            ? Haptics.NotificationFeedbackType.Error
            : result.risk_level === 'amber'
              ? Haptics.NotificationFeedbackType.Warning
              : Haptics.NotificationFeedbackType.Success,
        );
      }
      if (result.block_template) {
        navigation.replace('SeniorBlock', { template: result.block_template });
      } else {
        setVerdict(result);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al analizar.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityRole="button" accessibilityLabel="Volver">
          <MaterialIcons name="arrow-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.title}>Analizar email</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={styles.preview} contentContainerStyle={{ padding: 16 }}>
        <Text style={styles.previewLabel}>Contenido recibido</Text>
        <Text style={styles.previewText}>{text}</Text>
      </ScrollView>

      {verdict && !loading && (
        <View style={[styles.result, { borderColor: RISK_COLOR[verdict.risk_level] }]}>
          <MaterialIcons
            name={verdict.risk_level === 'green' ? 'check-circle' : 'warning'}
            size={32}
            color={RISK_COLOR[verdict.risk_level]}
          />
          <Text style={[styles.resultLabel, { color: RISK_COLOR[verdict.risk_level] }]}>
            {RISK_LABEL[verdict.risk_level]}
          </Text>
        </View>
      )}

      {error !== '' && <Text style={styles.error}>{error}</Text>}

      {!verdict && (
        <Pressable
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleAnalyze}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel="Analizar este email"
        >
          {loading
            ? <ActivityIndicator color={colors.white} />
            : <Text style={styles.btnText}>Analizar este email</Text>
          }
        </Pressable>
      )}

      {verdict && verdict.risk_level !== 'red' && (
        <Pressable
          style={[styles.btn, styles.btnSecondary]}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
        >
          <Text style={[styles.btnText, { color: colors.primary }]}>Volver</Text>
        </Pressable>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 16,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  title: { fontSize: 20, fontWeight: fontWeight.bold, color: colors.primary },
  preview: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 12,
    marginBottom: 16,
  },
  previewLabel: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.7,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  previewText: { fontSize: fontSize.body, color: colors.primary, lineHeight: 22 },
  result: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 2,
    padding: 16,
    marginBottom: 16,
  },
  resultLabel: { fontSize: fontSize.body, fontWeight: fontWeight.bold },
  error: { fontSize: fontSize.caption, color: colors.alert, marginBottom: 12, textAlign: 'center' },
  btn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  btnDisabled: { opacity: 0.6 },
  btnSecondary: { backgroundColor: colors.background, borderWidth: 1.5, borderColor: colors.primary },
  btnText: { color: colors.white, fontWeight: fontWeight.bold, fontSize: fontSize.body },
});
