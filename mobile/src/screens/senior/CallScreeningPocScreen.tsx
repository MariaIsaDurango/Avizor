import { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  NativeModules,
  NativeEventEmitter,
  Pressable,
  StyleSheet,
  AppState,
  Platform,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import { colors } from '../../constants/colors';

const { AvizorCallScreening } = NativeModules;
const emitter = new NativeEventEmitter(AvizorCallScreening);

type CallEvent = { number: string; direction: 'incoming' | 'outgoing'; ts: number };

type Props = NativeStackScreenProps<RootStackParamList, 'CallScreeningPoc'>;

export default function CallScreeningPocScreen({ navigation }: Props) {
  const [hasRole, setHasRole] = useState<boolean | null>(null);
  const [events, setEvents] = useState<CallEvent[]>([]);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    if (Platform.OS !== 'android') return;

    AvizorCallScreening.hasRole().then(setHasRole);

    const sub = AppState.addEventListener('change', (next) => {
      if (appState.current?.match(/inactive|background/) && next === 'active') {
        AvizorCallScreening.hasRole().then(setHasRole);
      }
      appState.current = next;
    });

    const eventSub = emitter.addListener('AvizorCallEvent', (...args: unknown[]) => {
      const e = args[0] as Omit<CallEvent, 'ts'>;
      setEvents((prev) => [{ ...e, ts: Date.now() }, ...prev].slice(0, 50));
    });

    return () => {
      sub.remove();
      eventSub.remove();
    };
  }, []);

  if (Platform.OS !== 'android') {
    return (
      <View style={styles.root}>
        <View style={styles.header}>
          <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityLabel="Volver">
            <Text style={styles.backIcon}>‹</Text>
          </Pressable>
          <Text style={styles.headerTitle}>PoC Llamadas</Text>
          <View style={{ width: 40 }} />
        </View>
        <View style={styles.content}>
          <Text style={{ color: colors.primary, textAlign: 'center', marginTop: 32 }}>
            Solo disponible en Android.
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      {/* ── Header ── */}
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityLabel="Volver">
          <Text style={styles.backIcon}>‹</Text>
        </Pressable>
        <Text style={styles.headerTitle}>PoC Llamadas</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.content}>
        {/* ── Estado del rol ── */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Rol de filtrado de llamadas</Text>
          {hasRole === null ? (
            <Text style={styles.statusText}>Comprobando…</Text>
          ) : (
            <View style={styles.statusRow}>
              <View style={[styles.dot, hasRole ? styles.dotGreen : styles.dotRed]} />
              <Text style={[styles.statusText, { color: hasRole ? colors.success : colors.alert }]}>
                {hasRole ? 'Concedido' : 'No concedido'}
              </Text>
            </View>
          )}

          {!hasRole && (
            <Pressable
              style={styles.btn}
              onPress={() => AvizorCallScreening.requestRole()}
              accessibilityRole="button"
              accessibilityLabel="Solicitar rol de filtrado de llamadas"
            >
              <Text style={styles.btnLabel}>Solicitar rol</Text>
            </Pressable>
          )}
        </View>

        {/* ── Llamadas capturadas ── */}
        <View style={[styles.card, styles.cardFlex]}>
          <View style={styles.eventsHeader}>
            <Text style={styles.cardTitle}>Llamadas capturadas</Text>
            <Text style={styles.eventsCount}>{events.length}</Text>
          </View>

          {events.length === 0 ? (
            <Text style={styles.empty}>
              {hasRole
                ? 'Realiza o recibe una llamada para ver eventos aquí.'
                : 'Solicita el rol para empezar a capturar llamadas.'}
            </Text>
          ) : (
            <FlatList
              data={events}
              keyExtractor={(_, i) => String(i)}
              contentContainerStyle={styles.list}
              renderItem={({ item }) => (
                <View style={styles.eventCard}>
                  <Text style={styles.eventDirection}>
                    {item.direction === 'incoming' ? '📲 Entrante' : '📞 Saliente'}
                  </Text>
                  <Text style={styles.eventNumber}>{item.number || '—'}</Text>
                  <Text style={styles.eventMeta}>{new Date(item.ts).toLocaleTimeString()}</Text>
                </View>
              )}
              ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
            />
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.background },

  header: {
    backgroundColor: colors.primary,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 48,
    paddingBottom: 12,
    paddingHorizontal: 16,
  },
  headerTitle: {
    color: colors.white,
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  backIcon: { color: colors.white, fontSize: 28, lineHeight: 28 },

  content: { flex: 1, padding: 16, gap: 16 },

  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    shadowColor: colors.primary,
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardFlex: { flex: 1 },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: 12,
  },

  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  dotGreen: { backgroundColor: colors.success },
  dotRed: { backgroundColor: colors.alert },
  statusText: { fontSize: 15, fontWeight: '600' },

  btn: {
    backgroundColor: colors.primary,
    borderRadius: 6,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    marginTop: 4,
  },
  btnLabel: { color: colors.white, fontSize: 15, fontWeight: '700' },

  eventsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  eventsCount: {
    backgroundColor: colors.primary,
    color: colors.white,
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  empty: { color: colors.primary, opacity: 0.5, fontSize: 14, textAlign: 'center', marginTop: 24 },
  list: { paddingBottom: 8 },

  eventCard: {
    backgroundColor: colors.background,
    borderRadius: 8,
    padding: 10,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
  },
  eventDirection: { fontSize: 12, fontWeight: '700', color: colors.primary, marginBottom: 2 },
  eventNumber: { fontSize: 15, color: '#1a1a1a', fontWeight: '600' },
  eventMeta: { fontSize: 10, color: '#5a6a6b', marginTop: 4 },
});
