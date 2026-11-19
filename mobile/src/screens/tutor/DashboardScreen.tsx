import { useState, useCallback } from 'react';
import { View, Text, Image, FlatList, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
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
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.brand}>
          <Image
            source={require('../../../assets/logo-web.png')}
            style={styles.logo}
            resizeMode="contain"
            accessibilityLabel=""
          />
          <Text style={styles.brandName}>Avizor</Text>
        </View>
        <Pressable
          onPress={() => navigation.navigate('TutorAccount')}
          style={styles.logoutBtn}
          accessibilityRole="button"
          accessibilityLabel="Ajustes de cuenta"
        >
          <MaterialIcons name="person" size={22} color={colors.primary} style={{ opacity: 0.45 }} />
        </Pressable>
      </View>

      {/* Section header + alerts list */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Alertas recientes</Text>
        {alerts.length > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{alerts.length}</Text>
          </View>
        )}
      </View>

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
            <View style={styles.emptyState}>
              <MaterialIcons name="notifications-none" size={52} color={colors.primary} style={styles.emptyIcon} />
              <Text style={styles.emptyText}>No hay alertas por el momento.</Text>
            </View>
          }
          ListFooterComponent={
            nextCursor ? (
              <Pressable
                onPress={handleLoadMore}
                disabled={loadingMore}
                style={styles.loadMoreBtn}
                accessibilityRole="button"
                accessibilityLabel="Cargar más alertas"
              >
                <Text style={styles.loadMoreText}>
                  {loadingMore ? 'Cargando…' : 'Cargar más'}
                </Text>
              </Pressable>
            ) : undefined
          }
        />
      )}

      {/* Footer actions */}
      <Pressable
        style={({ pressed }) => [styles.linkCard, pressed && styles.linkCardPressed]}
        onPress={() => navigation.navigate('TutorPairing')}
        accessibilityRole="button"
        accessibilityLabel="Vincular dispositivo sénior"
      >
        <MaterialIcons name="add-circle-outline" size={20} color={colors.primary} />
        <Text style={styles.linkCardText}>Vincular dispositivo sénior</Text>
      </Pressable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 16,
    paddingBottom: 20,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logo: {
    width: 32,
    height: 32,
  },
  brandName: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    fontStyle: 'italic',
  },
  logoutBtn: {
    padding: 8,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  badge: {
    backgroundColor: colors.alert,
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  badgeText: {
    color: colors.white,
    fontSize: 11,
    fontWeight: fontWeight.bold,
  },
  loader: {
    marginTop: 48,
  },
  list: {
    paddingBottom: 8,
    flexGrow: 1,
  },
  emptyState: {
    alignItems: 'center',
    marginTop: 48,
    gap: 12,
  },
  emptyIcon: {
    opacity: 0.25,
  },
  emptyText: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.5,
    textAlign: 'center',
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
  loadMoreBtn: {
    marginTop: 16,
    paddingVertical: 12,
    alignItems: 'center',
  },
  loadMoreText: {
    fontSize: fontSize.body,
    color: colors.primary,
    fontWeight: fontWeight.bold,
    textDecorationLine: 'underline',
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
    marginTop: 24,
  },
  linkCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 16,
    paddingVertical: 14,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderStyle: 'dashed',
  },
  linkCardPressed: {
    opacity: 0.6,
  },
  linkCardText: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
});
