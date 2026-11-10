import { useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { updateAlert, AlertStatus, ThreatType, Channel } from '../../services/alerts';

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

  const isResolved = alert.status === 'confirmed_fraud' || alert.status === 'false_positive';

  return (
    <Screen scrollable>
      <View style={styles.header}>
        <MaterialIcons name="warning" size={32} color={colors.alert} />
        <Text style={styles.seniorName}>{alert.senior_name}</Text>
        <Text style={styles.meta}>
          {THREAT_LABELS[alert.threat_type]} · {CHANNEL_LABELS[alert.channel]}
        </Text>
        <Text style={styles.date}>{formatDate(alert.created_at)}</Text>
      </View>

      <View style={styles.statusRow}>
        <Text style={styles.statusLabel}>Estado:</Text>
        <Text style={[styles.statusValue, isResolved && styles.statusResolved]}>
          {STATUS_LABELS[alert.status]}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Resumen</Text>
        <Text style={styles.sectionBody}>{alert.summary}</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Explicación</Text>
        <Text style={styles.sectionBody}>{alert.explanation}</Text>
      </View>

      {error !== null && <Text style={styles.error}>{error}</Text>}

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
});
