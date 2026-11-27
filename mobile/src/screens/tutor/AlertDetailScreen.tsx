import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { updateAlert, AlertStatus, ThreatType, Channel, Evidence, IndicatorEvidence } from '../../services/alerts';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'AlertDetail'>;

const THREAT_LABELS: Record<ThreatType, string> = {
  phishing: 'Phishing',
  smishing: 'Smishing',
  vishing: 'Vishing',
  spam: 'Spam',
  identity_theft: 'Robo de identidad',
  bank_fraud: 'Fraude bancario',
  other: 'Amenaza detectada',
  none: 'Alerta',
};

const CHANNEL_LABELS: Record<Channel, string> = {
  sms: 'SMS',
  notification: 'Notificación',
  screen: 'Pantalla',
  call: 'Llamada',
  manual: 'Envío manual',
};

const STATUS_LABELS: Record<AlertStatus, string> = {
  new: 'Nueva',
  seen: 'Vista',
  confirmed_fraud: 'Fraude confirmado',
  false_positive: 'Falso positivo',
};

const INDICATOR_LABELS: Record<IndicatorEvidence['type'], string> = {
  domain: 'Dominio',
  url: 'URL',
  phone: 'Teléfono',
  alphanumeric_sender: 'Remitente',
};

const RAG_SOURCE_LABELS: Record<string, string> = {
  incibe: 'INCIBE',
  osi: 'OSI',
  policia_nacional: 'Policía Nacional',
};

function EvidenceItem({ item, largeText }: { item: Evidence; largeText: boolean }) {
  if (item.type === 'official_notice') {
    return (
      <View style={styles.evidenceRow}>
        <MaterialIcons name="verified" size={16} color={colors.primary} style={{ marginTop: 2 }} />
        <View style={{ flex: 1 }}>
          <Text style={[styles.evidenceSource, largeText && { fontSize: 17 }]}>{RAG_SOURCE_LABELS[item.source] ?? item.source}</Text>
          <Text style={[styles.evidenceUrl, largeText && { fontSize: 15 }]} numberOfLines={1}>{item.url}</Text>
        </View>
      </View>
    );
  }
  return (
    <View style={styles.evidenceRow}>
      <MaterialIcons name="info-outline" size={16} color={colors.warning} style={{ marginTop: 2 }} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.evidenceLabel, largeText && { fontSize: 17 }]}>
          {INDICATOR_LABELS[item.type]}: <Text style={styles.evidenceValue}>{item.value}</Text>
        </Text>
        <Text style={[styles.evidenceReason, largeText && { fontSize: 17 }]}>{item.reason}</Text>
      </View>
    </View>
  );
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AlertDetailScreen({ route, navigation }: Props) {
  const { largeText } = useAccessibility();
  const [alert, setAlert] = useState(route.params.alert);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpdate(status: Exclude<AlertStatus, 'new'>) {
    setLoading(true);
    setError(null);
    try {
      const updated = await updateAlert(alert.id, status);
      setAlert(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al actualizar la alerta.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (alert.status === 'new') {
      updateAlert(alert.id, 'seen')
        .then(setAlert)
        .catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isResolved = alert.status === 'confirmed_fraud' || alert.status === 'false_positive';

  return (
    <Screen scrollable>
      <View style={styles.header}>
        <MaterialIcons name="warning" size={32} color={colors.alert} />
        <Text style={[styles.seniorName, largeText && { fontSize: 32 }]}>{alert.senior_name}</Text>
        <Text style={[styles.meta, largeText && { fontSize: 22 }]}>
          {THREAT_LABELS[alert.threat_type]} · {CHANNEL_LABELS[alert.channel]}
        </Text>
        <Text style={[styles.date, largeText && { fontSize: 22 }]}>{formatDate(alert.created_at)}</Text>
      </View>

      <View style={styles.statusRow}>
        <Text style={[styles.statusLabel, largeText && { fontSize: 22 }]}>Estado:</Text>
        <Text style={[styles.statusValue, isResolved && styles.statusResolved, largeText && { fontSize: 22 }]}>
          {STATUS_LABELS[alert.status]}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, largeText && { fontSize: 22 }]}>Resumen</Text>
        <Text style={[styles.sectionBody, largeText && { fontSize: 22 }]}>{alert.summary}</Text>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, largeText && { fontSize: 22 }]}>Explicación</Text>
        <Text style={[styles.sectionBody, largeText && { fontSize: 22 }]}>{alert.explanation}</Text>
      </View>

      {alert.evidence.length > 0 && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, largeText && { fontSize: 22 }]}>Indicadores técnicos</Text>
          {alert.evidence.map((item, i) => (
            <EvidenceItem key={i} item={item} largeText={largeText} />
          ))}
        </View>
      )}

      {error !== null && <Text style={[styles.error, largeText && { fontSize: 22 }]}>{error}</Text>}

      {loading && <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />}

      {!loading && !isResolved && (
        <View style={styles.actions}>
          {alert.status === 'new' && (
            <Button
              label="Marcar como vista"
              onPress={() => handleUpdate('seen')}
            />
          )}
          <Button
            label="Confirmar fraude"
            variant="alert"
            onPress={() => handleUpdate('confirmed_fraud')}
          />
          <Button
            label="Falso positivo"
            variant="action"
            onPress={() => handleUpdate('false_positive')}
          />
        </View>
      )}

      {!loading && isResolved && (
        <View style={styles.actions}>
          <Button
            label="Volver al panel"
            onPress={() => navigation.goBack()}
          />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    paddingVertical: 24,
    gap: 6,
  },
  seniorName: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  meta: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.7,
  },
  date: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.5,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  statusLabel: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  statusValue: {
    fontSize: fontSize.body,
    color: colors.alert,
    fontWeight: fontWeight.bold,
  },
  statusResolved: {
    color: colors.success,
  },
  section: {
    marginBottom: 20,
    gap: 6,
  },
  sectionTitle: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  sectionBody: {
    fontSize: fontSize.body,
    color: colors.primary,
    lineHeight: 26,
  },
  actions: {
    gap: 12,
    marginTop: 8,
    paddingBottom: 24,
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
    marginBottom: 12,
  },
  loader: {
    marginVertical: 16,
  },
  evidenceRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: colors.primary + '14',
  },
  evidenceLabel: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: fontWeight.bold,
  },
  evidenceValue: {
    fontWeight: '400',
  },
  evidenceReason: {
    fontSize: 13,
    color: colors.primary,
    opacity: 0.65,
    marginTop: 2,
  },
  evidenceSource: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: fontWeight.bold,
  },
  evidenceUrl: {
    fontSize: 12,
    color: colors.primary,
    opacity: 0.55,
    marginTop: 1,
  },
});
