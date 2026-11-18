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
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import { colors } from '../../constants/colors';

const { AvizorAccessibility } = NativeModules;
const emitter = new NativeEventEmitter(AvizorAccessibility);

type TextEvent = { text: string; packageName: string; eventType: string; ts: number };

type Props = NativeStackScreenProps<RootStackParamList, 'AccessibilityPoc'>;

export default function AccessibilityPocScreen({ navigation }: Props) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [events, setEvents] = useState<TextEvent[]>([]);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    AvizorAccessibility.isServiceEnabled().then(setEnabled);

    // Refresca al volver desde ajustes de accesibilidad
    const sub = AppState.addEventListener('change', (next) => {
      if (appState.current.match(/inactive|background/) && next === 'active') {
        AvizorAccessibility.isServiceEnabled().then(setEnabled);
      }
      appState.current = next;
    });

    const eventSub = emitter.addListener('AvizorTextEvent', (e: Omit<TextEvent, 'ts'>) => {
      setEvents((prev) => [{ ...e, ts: Date.now() }, ...prev].slice(0, 50));
    });

    return () => {
      sub.remove();
      eventSub.remove();
    };
  }, []);

  return (
    <View style={styles.root}>
      {/* ── Header (navbar style) ── */}
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityLabel="Volver">
          <Text style={styles.backIcon}>‹</Text>
        </Pressable>
        <Text style={styles.headerTitle}>PoC Accesibilidad</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.content}>
        {/* ── Estado del servicio ── */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Estado del servicio</Text>
          {enabled === null ? (
            <Text style={styles.statusText}>Comprobando…</Text>
          ) : (
            <View style={styles.statusRow}>
              <View style={[styles.dot, enabled ? styles.dotGreen : styles.dotRed]} />
              <Text style={[styles.statusText, { color: enabled ? colors.success : colors.alert }]}>
                {enabled ? 'Activo' : 'Inactivo'}
              </Text>
            </View>
          )}

          {!enabled && (
            <Pressable
              style={styles.btn}
              onPress={() => AvizorAccessibility.openSettings()}
              accessibilityRole="button"
              accessibilityLabel="Activar en ajustes de accesibilidad"
            >
              <Text style={styles.btnLabel}>Activar en Ajustes</Text>
            </Pressable>
          )}
        </View>

        {/* ── Eventos capturados ── */}
        <View style={[styles.card, styles.cardFlex]}>
          <View style={styles.eventsHeader}>
            <Text style={styles.cardTitle}>Eventos capturados</Text>
            <Text style={styles.eventsCount}>{events.length}</Text>
          </View>

          {events.length === 0 ? (
            <Text style={styles.empty}>
              {enabled
                ? 'Interactúa con otra app para ver eventos aquí.'
                : 'Activa el servicio para empezar a capturar.'}
            </Text>
          ) : (
            <FlatList
              data={events}
              keyExtractor={(_, i) => String(i)}
              contentContainerStyle={styles.list}
              renderItem={({ item }) => (
                <View style={styles.eventCard}>
                  <Text style={styles.eventPackage}>{item.packageName || '—'}</Text>
                  <Text style={styles.eventText} numberOfLines={3}>{item.text}</Text>
                  <Text style={styles.eventMeta}>{item.eventType}</Text>
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

  // Header (teal navbar)
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

  // Cards (web-style)
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

  // Status
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  dotGreen: { backgroundColor: colors.success },
  dotRed: { backgroundColor: colors.alert },
  statusText: { fontSize: 15, fontWeight: '600' },

  // Button (web primary style)
  btn: {
    backgroundColor: colors.primary,
    borderRadius: 6,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    marginTop: 4,
  },
  btnLabel: { color: colors.white, fontSize: 15, fontWeight: '700' },

  // Events
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
  eventPackage: { fontSize: 11, fontWeight: '700', color: colors.primary, marginBottom: 2 },
  eventText: { fontSize: 13, color: '#1a1a1a', lineHeight: 18 },
  eventMeta: { fontSize: 10, color: '#5a6a6b', marginTop: 4 },
});
