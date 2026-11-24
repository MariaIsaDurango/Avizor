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
import { getSenior, GuardianSeniorInfo } from '../../services/pairing';
import { getStatsSummary } from '../../services/stats';
import { getMe } from '../../services/auth';

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

function formatRelative(iso: string): string {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (h < 1) return 'hace menos de 1 hora';
  if (h < 24) return `hace ${h} hora${h > 1 ? 's' : ''}`;
  const d = Math.floor(h / 24);
  return `hace ${d} día${d > 1 ? 's' : ''}`;
}

export default function TutorDashboardScreen({ navigation }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [senior, setSenior] = useState<GuardianSeniorInfo | null>(null);
  const [tutorName, setTutorName] = useState<string>('');
  const [attacksTotal, setAttacksTotal] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [page, seniorData, me, stats] = await Promise.all([
        getAlerts(),
        getSenior(),
        getMe().catch(() => null),
        getStatsSummary(7).catch(() => null),
      ]);
      setAlerts(page.items);
      setNextCursor(page.next_cursor);
      setSenior(seniorData);
      if (me) setTutorName(me.display_name);
      if (stats) setAttacksTotal(stats.total);
    } catch {
      setError('No se pudieron cargar las alertas.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { fetchData(); }, [fetchData]));

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

  const seniorInitial = senior?.senior_display_name?.charAt(0).toUpperCase() ?? '?';

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

      {loading && (
        <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
      )}

      {error !== null && <Text style={styles.error}>{error}</Text>}

      {!loading && (
        <FlatList
          data={alerts}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <View>
              {/* Greeting */}
              {tutorName ? (
                <View style={styles.greeting}>
                  <Text style={styles.greetingTitle}>Hola, {tutorName}</Text>
                  <Text style={styles.greetingSubtitle}>Aquí tienes el resumen de actividad.</Text>
                </View>
              ) : null}

              {/* Senior card or link button */}
              {senior ? (
                <View style={styles.card}>
                  <Text style={styles.cardTitle}>Sénior vinculado</Text>
                  <View style={styles.seniorHeader}>
                    <View style={styles.seniorAvatar}>
                      <Text style={styles.seniorAvatarText}>{seniorInitial}</Text>
                    </View>
                    <View style={styles.seniorInfo}>
                      <Text style={styles.seniorName}>{senior.senior_display_name}</Text>
                      <View style={styles.seniorStatusRow}>
                        <View style={styles.statusDot} />
                        <Text style={styles.seniorStatusText}>Activo</Text>
                      </View>
                    </View>
                  </View>
                  {(senior.platform || senior.last_seen_at) && (
                    <View style={styles.seniorMeta}>
                      {senior.platform && (
                        <Text style={styles.seniorMetaText}>
                          Plataforma: {senior.platform}
                        </Text>
                      )}
                      {senior.last_seen_at && (
                        <Text style={styles.seniorMetaText}>
                          Última actividad: {formatRelative(senior.last_seen_at)}
                        </Text>
                      )}
                    </View>
                  )}
                </View>
              ) : (
                <Pressable
                  style={({ pressed }) => [styles.linkCard, pressed && styles.linkCardPressed]}
                  onPress={() => navigation.navigate('TutorPairing')}
                  accessibilityRole="button"
                  accessibilityLabel="Vincular dispositivo sénior"
                >
                  <MaterialIcons name="add-circle-outline" size={20} color={colors.primary} />
                  <Text style={styles.linkCardText}>Vincular dispositivo sénior</Text>
                </Pressable>
              )}

              {/* Stats card */}
              {attacksTotal !== null && (
                <View style={styles.card}>
                  <Text style={styles.cardTitle}>Ataques detectados</Text>
                  <Text style={styles.statValue}>{attacksTotal}</Text>
                  <Text style={styles.statLabel}>en Avizor · últimos 7 días</Text>
                </View>
              )}

              {/* Alerts section header */}
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>Alertas recientes</Text>
                {alerts.length > 0 && (
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{alerts.length}</Text>
                  </View>
                )}
              </View>
            </View>
          }
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
  loader: {
    marginTop: 48,
  },
  list: {
    paddingBottom: 8,
    flexGrow: 1,
  },
  greeting: {
    marginBottom: 20,
  },
  greetingTitle: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  greetingSubtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.6,
    marginTop: 2,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.primary,
    borderStyle: 'solid',
    gap: 4,
  },
  cardTitle: {
    fontSize: 12,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  seniorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  seniorAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  seniorAvatarText: {
    color: colors.white,
    fontSize: 20,
    fontWeight: fontWeight.bold,
  },
  seniorInfo: {
    flex: 1,
    gap: 4,
  },
  seniorName: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  seniorStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.success,
  },
  seniorStatusText: {
    fontSize: 13,
    color: colors.success,
    fontWeight: fontWeight.bold,
  },
  seniorMeta: {
    marginTop: 8,
    gap: 4,
  },
  seniorMetaText: {
    fontSize: 12,
    color: colors.primary,
    opacity: 0.6,
  },
  statValue: {
    fontSize: 40,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    lineHeight: 48,
  },
  statLabel: {
    fontSize: 13,
    color: colors.primary,
    opacity: 0.6,
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
    marginBottom: 16,
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
