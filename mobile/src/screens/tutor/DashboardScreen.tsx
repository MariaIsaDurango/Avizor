import { useState, useCallback } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import AlertCard from '../../components/AlertCard';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { getAlerts, Alert, ThreatType } from '../../services/alerts';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorDashboard'>;

const THREAT_ICONS: Record<ThreatType, keyof typeof MaterialIcons.glyphMap> = {
  phishing: 'email',
  smishing: 'sms',
  vishing: 'call',
  spam: 'block',
  identity_theft: 'person',
  bank_fraud: 'attach-money',
  other: 'warning',
  none: 'info',
};

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export default function TutorDashboardScreen({ navigation }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await getAlerts();
      setAlerts(page.items);
      setNextCursor(page.next_cursor);
    } catch {
      setError('No se pudieron cargar las alertas.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { fetchAlerts(); }, [fetchAlerts]));

  async function handleLoadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await getAlerts(nextCursor);
      setAlerts((prev) => [...prev, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch {
      // fallo silencioso en paginación
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <Screen style={styles.screen}>
      <Text style={styles.title}>Panel de control</Text>

      <View style={styles.content}>
        {loading && (
          <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
        )}

        {error !== null && <Text style={styles.error}>{error}</Text>}

        {!loading && (
          <FlatList
            data={alerts}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.list}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => navigation.navigate('AlertDetail', { alert: item })}
                accessibilityRole="button"
                accessibilityLabel={`Alerta de ${item.senior_name}: ${item.summary}`}
              >
                {item.status === 'new' && (
                  <View style={styles.newBadge}>
                    <Text style={styles.newLabel}>NUEVA</Text>
                  </View>
                )}
                <AlertCard
                  icon={THREAT_ICONS[item.threat_type]}
                  title={item.senior_name}
                  description={`${item.summary} · ${formatDate(item.created_at)}`}
                  riskLevel="red"
                />
              </Pressable>
            )}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
            ListEmptyComponent={
              <Text style={styles.empty}>No hay alertas por el momento.</Text>
            }
            ListFooterComponent={
              nextCursor ? (
                <Button
                  label={loadingMore ? 'Cargando...' : 'Cargar más'}
                  onPress={handleLoadMore}
                  disabled={loadingMore}
                  style={styles.loadMore}
                />
              ) : undefined
            }
          />
        )}
      </View>

      <View style={styles.footer}>
        <Button
          label="Vincular dispositivo Sénior"
          onPress={() => navigation.navigate('TutorPairing')}
        />
        <Button
          label="Cerrar sesión"
          variant="alert"
          onPress={() => navigation.navigate('TutorLogout')}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingBottom: 40,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginTop: 24,
    marginBottom: 16,
    textAlign: 'center',
  },
  content: {
    flex: 1,
  },
  loader: {
    flex: 1,
  },
  list: {
    paddingBottom: 8,
  },
  empty: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
    marginTop: 48,
    opacity: 0.6,
  },
  separator: {
    height: 12,
  },
  newBadge: {
    alignSelf: 'flex-end',
    backgroundColor: colors.alert,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 4,
  },
  newLabel: {
    color: colors.white,
    fontSize: 12,
    fontWeight: fontWeight.bold,
  },
  loadMore: {
    marginTop: 16,
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
    marginTop: 24,
  },
  footer: {
    gap: 12,
    marginTop: 16,
  },
});
