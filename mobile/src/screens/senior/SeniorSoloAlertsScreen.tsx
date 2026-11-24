import { useState, useCallback } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator, useWindowDimensions } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { MaterialIcons } from '@expo/vector-icons';
import { PieChart } from 'react-native-chart-kit';
import Screen from '../../components/Screen';
import AlertCard from '../../components/AlertCard';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { getAlerts, Alert, ThreatType } from '../../services/alerts';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorSoloAlerts'>;

const THREAT_ICONS: Record<ThreatType, keyof typeof MaterialIcons.glyphMap> = {
  phishing:       'email',
  smishing:       'sms',
  vishing:        'call',
  spam:           'block',
  identity_theft: 'person',
  bank_fraud:     'attach-money',
  other:          'warning',
  none:           'info',
};

const THREAT_LABELS: Record<string, string> = {
  phishing:       'Phishing',
  smishing:       'Smishing',
  vishing:        'Vishing',
  spam:           'Spam',
  identity_theft: 'Id. theft',
  bank_fraud:     'Fraude bancario',
  other:          'Otro',
};

const THREAT_COLORS = ['#164E55','#D93838','#D97706','#0F2C59','#2E8B57','#F4B19B','#1d6b74'];

function buildPieData(byThreatType: Record<string, number>) {
  return Object.entries(byThreatType)
    .filter(([k, v]) => k !== 'none' && v > 0)
    .map(([k, v], i) => ({
      name: THREAT_LABELS[k] ?? k,
      population: v,
      color: THREAT_COLORS[i % THREAT_COLORS.length],
      legendFontColor: colors.primary,
      legendFontSize: 12,
    }));
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
}

export default function SeniorSoloAlertsScreen({ navigation }: Props) {
  const { width }                             = useWindowDimensions();
  const [alerts, setAlerts]       = useState<Alert[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading]     = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError]         = useState<string | null>(null);

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
      setAlerts(prev => [...prev, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch {}
    finally { setLoadingMore(false); }
  }

  const byThreatType: Record<string, number> = {};
  for (const a of alerts) {
    if (a.threat_type && a.threat_type !== 'none') {
      byThreatType[a.threat_type] = (byThreatType[a.threat_type] || 0) + 1;
    }
  }
  const attacksTotal = Object.values(byThreatType).reduce((s, n) => s + n, 0);
  const pieData = buildPieData(byThreatType);

  return (
    <Screen style={styles.screen}>
      <View style={styles.header}>
        <Pressable
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          accessibilityRole="button"
          accessibilityLabel="Volver"
        >
          <MaterialIcons name="arrow-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.title}>Mis alertas</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading && <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />}
      {error !== null && <Text style={styles.error}>{error}</Text>}

      {!loading && (
        <FlatList
          data={alerts}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.list}
          ListHeaderComponent={
            <View>
              {attacksTotal > 0 && (
                <View style={styles.statsCard}>
                  <Text style={styles.statsLabel}>Amenazas detectadas</Text>
                  <Text style={styles.statsValue}>{attacksTotal}</Text>
                </View>
              )}

              {pieData.length > 0 && (
                <View style={styles.chartCard}>
                  <Text style={styles.statsLabel}>Por tipo de amenaza</Text>
                  <PieChart
                    data={pieData}
                    width={width - 40}
                    height={160}
                    chartConfig={{ color: (opacity = 1) => `rgba(22, 78, 85, ${opacity})` }}
                    accessor="population"
                    backgroundColor="transparent"
                    paddingLeft="15"
                    hasLegend={false}
                  />
                  <View style={styles.legend}>
                    {pieData.map((item, i) => (
                      <View key={i} style={styles.legendItem}>
                        <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                        <Text style={styles.legendLabel}>{item.name}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}

              {alerts.length > 0 && (
                <View style={styles.sectionHeader}>
                  <Text style={styles.sectionTitle}>Alertas recientes</Text>
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{alerts.length}</Text>
                  </View>
                </View>
              )}
            </View>
          }
          renderItem={({ item }) => (
            <Pressable
              onPress={() => navigation.navigate('AlertDetail', { alert: item })}
              accessibilityRole="button"
              accessibilityLabel={`Alerta: ${item.summary}`}
            >
              {item.status === 'new' && (
                <View style={styles.newBadge}>
                  <Text style={styles.newLabel}>NUEVA</Text>
                </View>
              )}
              <AlertCard
                icon={THREAT_ICONS[item.threat_type]}
                title={item.summary}
                description={formatDate(item.created_at)}
                riskLevel="red"
              />
            </Pressable>
          )}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <MaterialIcons name="notifications-none" size={52} color={colors.primary} style={styles.emptyIcon} />
              <Text style={styles.emptyText}>No tienes alertas por el momento.</Text>
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
  screen:   { paddingBottom: 24 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 20,
  },
  backBtn:  { width: 40, alignItems: 'flex-start' },
  title: {
    fontSize: 20,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  loader:   { marginTop: 48 },
  list:     { paddingBottom: 8, flexGrow: 1 },
  statsCard: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  chartCard: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  statsLabel: {
    fontSize: 12,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  statsValue: {
    fontSize: 40,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    lineHeight: 48,
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
  badgeText: { color: colors.white, fontSize: 11, fontWeight: fontWeight.bold },
  emptyState: { alignItems: 'center', marginTop: 48, gap: 12 },
  emptyIcon:  { opacity: 0.25 },
  emptyText: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.5,
    textAlign: 'center',
  },
  newBadge: {
    alignSelf: 'flex-end',
    backgroundColor: colors.alert,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 4,
  },
  newLabel: { color: colors.white, fontSize: 12, fontWeight: fontWeight.bold },
  loadMoreBtn: { marginTop: 16, paddingVertical: 12, alignItems: 'center' },
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
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendLabel: { fontSize: 12, color: colors.primary },
});
