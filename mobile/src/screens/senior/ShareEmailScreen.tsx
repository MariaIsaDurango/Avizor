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
import { submitAnalysis, submitAnalysisWithFile, Verdict } from '../../services/analyses';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorShareEmail'>;

const RISK_LABEL: Record<string, string> = {
  green: 'Sin señales de riesgo',
  amber: 'Sospechoso',
  red: 'Peligroso, no hagas clic',
};

const RISK_COLOR: Record<string, string> = {
  green: colors.success,
  amber: colors.warning,
  red: colors.alert,
};

const RISK_COLOR_COLORBLIND: Record<string, string> = {
  green: colors.successColorBlind,
  amber: colors.warning,
  red: colors.alert,
};

// issue #192: añadir image/* al intent-filter del Manifest y los tipos de abajo (sin gif — contrato solo acepta jpeg, png, webp, heic)
// 'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'
const SUPPORTED_MIME_TYPES = [
  'application/pdf',
];

const THREAT_LABEL: Record<string, string> = {
  phishing:       'Parece un intento de robo de datos por email o web falsa.',
  smishing:       'Parece un intento de fraude por SMS.',
  vishing:        'Parece un intento de fraude por llamada telefónica.',
  spam:           'Contenido publicitario no solicitado.',
  identity_theft: 'Parece un intento de robo de identidad.',
  bank_fraud:     'Parece un intento de fraude bancario.',
  other:          'Contenido sospechoso sin categoría definida.',
  none:           'El sistema detectó anomalías pero no pudo clasificar el tipo de amenaza.',
};

export default function ShareEmailScreen({ route, navigation }: Props) {
  const { text, fileUri, mimeType } = route.params;
  const { hardOfHearing, largeText, colorBlind } = useAccessibility();
  const [loading, setLoading] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [showReason, setShowReason] = useState(false);
  const [error, setError] = useState<string>(() => {
    if (fileUri && mimeType && !SUPPORTED_MIME_TYPES.includes(mimeType)) {
      const ext = mimeType.split('/')[1]?.toUpperCase() ?? mimeType;
      return `El formato ${ext} no se acepta. Solo se admiten PDF, JPG, PNG y WebP.`;
    }
    return '';
  });
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
      const result = fileUri && mimeType
        ? await submitAnalysisWithFile(deviceId, fileUri, mimeType)
        : await submitAnalysis(deviceId, 'text', (text ?? '').slice(0, 5000));
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
        <Text style={[styles.title, largeText && styles.titleLarge]}>{fileUri ? 'Analizar archivo' : 'Analizar email'}</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.preview}>
        <Text style={[styles.previewLabel, largeText && styles.previewLabelLarge]}>Contenido recibido</Text>
        {fileUri ? (
          <View style={styles.filePreview}>
            <MaterialIcons
              name={mimeType === 'application/pdf' ? 'picture-as-pdf' : 'image'}
              size={largeText ? 56 : 40}
              color={colors.primary}
              style={{ opacity: 0.7 }}
            />
            <Text style={[styles.fileName, largeText && styles.fileNameLarge]}>
              {mimeType === 'application/pdf' ? 'Documento PDF' : 'Imagen'}
            </Text>
            <Text style={[styles.fileNote, largeText && styles.fileNoteLarge]}>Máximo 10 MB</Text>
          </View>
        ) : (
          <ScrollView>
            <Text style={[styles.previewText, largeText && styles.previewTextLarge]}>{text}</Text>
          </ScrollView>
        )}
      </View>

      {verdict && !loading && (
        <>
          <View
            style={[styles.result, { borderColor: (colorBlind ? RISK_COLOR_COLORBLIND : RISK_COLOR)[verdict.risk_level] }]}
            accessibilityLiveRegion="polite"
            accessibilityLabel={`Resultado: ${RISK_LABEL[verdict.risk_level]}`}
          >
            <MaterialIcons
              name={verdict.risk_level === 'green' ? 'check-circle' : 'warning'}
              size={largeText ? 48 : 36}
              color={(colorBlind ? RISK_COLOR_COLORBLIND : RISK_COLOR)[verdict.risk_level]}
              accessibilityLabel={`Nivel de riesgo: ${RISK_LABEL[verdict.risk_level]}`}
            />
            {colorBlind && (
              <Text style={[styles.resultBadge, { color: (RISK_COLOR_COLORBLIND)[verdict.risk_level] }]}>
                {verdict.risk_level.toUpperCase()}
              </Text>
            )}
            <Text style={[styles.resultLabel, largeText && styles.resultLabelLarge, { color: (colorBlind ? RISK_COLOR_COLORBLIND : RISK_COLOR)[verdict.risk_level] }]}>
              {RISK_LABEL[verdict.risk_level]}
            </Text>
          </View>
          {verdict.risk_level === 'amber' && (
            <>
              <Pressable
                style={styles.reasonBtn}
                onPress={() => setShowReason(v => !v)}
                accessibilityRole="button"
                accessibilityLabel={showReason ? 'Ocultar motivo' : 'Ver motivo'}
              >
                <Text style={[styles.reasonBtnText, largeText && styles.reasonBtnTextLarge]}>
                  {showReason ? 'Ocultar motivo' : 'Ver motivo'}
                </Text>
                <MaterialIcons
                  name={showReason ? 'expand-less' : 'expand-more'}
                  size={largeText ? 26 : 20}
                  color={colors.primary}
                />
              </Pressable>
              {showReason && (
                <View style={styles.reasonBox}>
                  <Text style={[styles.reasonText, largeText && styles.reasonTextLarge]}>
                    {THREAT_LABEL[verdict.threat_type] ?? 'Contenido marcado como sospechoso.'}
                  </Text>
                </View>
              )}
            </>
          )}
        </>
      )}

      {error !== '' && <Text style={[styles.error, largeText && styles.errorLarge]} accessibilityLiveRegion="assertive">{error}</Text>}

      {!verdict && (
        <Pressable
          style={[styles.btn, (loading || (!!fileUri && !!mimeType && !SUPPORTED_MIME_TYPES.includes(mimeType))) && styles.btnDisabled]}
          onPress={handleAnalyze}
          disabled={loading || (!!fileUri && !!mimeType && !SUPPORTED_MIME_TYPES.includes(mimeType))}
          accessibilityRole="button"
          accessibilityLabel={loading ? 'Analizando, por favor espera' : fileUri ? (mimeType === 'application/pdf' ? 'Analizar este PDF' : 'Analizar esta imagen') : 'Analizar este email'}
          accessibilityState={{ busy: loading }}
        >
          {loading
            ? <ActivityIndicator color={colors.white} accessibilityLabel="Analizando archivo" />
            : <Text style={[styles.btnText, largeText && styles.btnTextLarge]}>{fileUri ? (mimeType === 'application/pdf' ? 'Analizar PDF' : 'Analizar imagen') : 'Analizar este email'}</Text>
          }
        </Pressable>
      )}

      {verdict && verdict.risk_level !== 'red' && (
        <Pressable
          style={[styles.btn, styles.btnSecondary]}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
        >
          <Text style={[styles.btnText, largeText && styles.btnTextLarge, { color: colors.primary }]}>Volver</Text>
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
  title: { flex: 1, fontSize: 20, fontWeight: fontWeight.bold, color: colors.primary, textAlign: 'center' },
  titleLarge: { fontSize: 24 },
  preview: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 12,
    marginBottom: 16,
    padding: 16,
  },
  filePreview: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 24,
  },
  fileName: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  fileNameLarge: { fontSize: 22 },
  fileNote: {
    fontSize: fontSize.caption,
    color: colors.primary,
    opacity: 0.5,
  },
  fileNoteLarge: { fontSize: 18 },
  previewLabel: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.7,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  previewLabelLarge: { fontSize: 16 },
  previewText: { fontSize: fontSize.body, color: colors.primary, lineHeight: 22 },
  previewTextLarge: { fontSize: 22, lineHeight: 30 },
  result: {
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 2,
    padding: 16,
    marginBottom: 16,
  },
  resultLabel: { fontSize: fontSize.body, fontWeight: fontWeight.bold, textAlign: 'center' },
  resultLabelLarge: { fontSize: 22 },
  resultBadge: { fontSize: 11, fontWeight: fontWeight.bold, letterSpacing: 2 },
  error: { fontSize: fontSize.caption, color: colors.alert, marginBottom: 12, textAlign: 'center' },
  errorLarge: { fontSize: 18 },
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
  btnTextLarge: { fontSize: 22 },
  reasonBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 8,
    marginBottom: 8,
  },
  reasonBtnText: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  reasonBtnTextLarge: { fontSize: 18 },
  reasonBox: {
    backgroundColor: colors.white,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  reasonText: {
    fontSize: fontSize.caption,
    color: colors.primary,
    lineHeight: 20,
  },
  reasonTextLarge: { fontSize: 18, lineHeight: 26 },
});
