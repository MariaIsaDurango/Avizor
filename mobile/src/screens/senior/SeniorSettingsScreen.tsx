import { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, Alert, AppState, Platform, NativeModules } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { apiFetch, clearToken } from '../../services/api';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { RootStackParamList } from '../../navigation/types';

const { AvizorCallScreening, AvizorNotification } = NativeModules;

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorSettings'>;

export default function SeniorSettingsScreen({ navigation }: Props) {
  const { largeText } = useAccessibility();
  const [callRole, setCallRole] = useState<boolean | null>(null);
  const [notifEnabled, setNotifEnabled] = useState<boolean | null>(null);
  const appState = useRef(AppState.currentState);

  function checkPermissions() {
    AvizorCallScreening?.hasRole().then(setCallRole).catch(() => setCallRole(false));
    AvizorNotification?.isServiceEnabled().then(setNotifEnabled).catch(() => setNotifEnabled(false));
  }

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    checkPermissions();
    const sub = AppState.addEventListener('change', (next) => {
      if (appState.current?.match(/inactive|background/) && next === 'active') checkPermissions();
      appState.current = next;
    });
    return () => sub.remove();
  }, []);

  function handleLogout() {
    Alert.alert(
      '¿Estás seguro?',
      'Necesitarás un nuevo código de tu familiar para volver a entrar.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Cerrar sesión',
          style: 'destructive',
          onPress: async () => {
            try { await apiFetch('/api/v1/senior/logout', { method: 'POST' }); } catch {}
            await clearToken();
            await Promise.allSettled([
              SecureStore.deleteItemAsync(STORAGE_KEYS.USER_MODE),
              SecureStore.deleteItemAsync(STORAGE_KEYS.DEVICE_ID),
              SecureStore.deleteItemAsync(STORAGE_KEYS.SENIOR_ID),
              SecureStore.deleteItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE),
              SecureStore.deleteItemAsync(STORAGE_KEYS.GUARDIAN_PHONE),
            ]);
            navigation.reset({ index: 0, routes: [{ name: 'Welcome' }] });
          },
        },
      ],
    );
  }

  const dotColor = (val: boolean | null) =>
    val === null ? colors.primary : val ? colors.success : colors.alert;
  const dotOpacity = (val: boolean | null) => val === null ? 0.25 : 1;

  return (
    <Screen>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityRole="button" accessibilityLabel="Volver">
          <MaterialIcons name="arrow-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={[styles.title, largeText && styles.titleLarge]}>Ajustes</Text>
        <View style={{ width: 40 }} />
      </View>

      {Platform.OS === 'android' && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, largeText && styles.sectionTitleLarge]}>Protección activa</Text>

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <View style={[styles.dot, { backgroundColor: dotColor(callRole), opacity: dotOpacity(callRole) }]} />
              <View>
                <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Filtrado de llamadas</Text>
                <Text style={styles.rowSub}>
                  {callRole === null ? 'Comprobando…' : callRole ? 'Activo' : 'Inactivo'}
                </Text>
              </View>
            </View>
            {callRole === false && (
              <Pressable
                style={styles.activateBtn}
                onPress={() => AvizorCallScreening?.requestRole()}
                accessibilityRole="button"
                accessibilityLabel="Activar filtrado de llamadas"
              >
                <Text style={styles.activateBtnText}>Activar</Text>
              </Pressable>
            )}
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <View style={[styles.dot, { backgroundColor: dotColor(notifEnabled), opacity: dotOpacity(notifEnabled) }]} />
              <View>
                <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Alertas de notificaciones</Text>
                <Text style={styles.rowSub}>
                  {notifEnabled === null ? 'Comprobando…' : notifEnabled ? 'Activo' : 'Inactivo'}
                </Text>
              </View>
            </View>
            {notifEnabled === false && (
              <Pressable
                style={styles.activateBtn}
                onPress={() => AvizorNotification?.openSettings()}
                accessibilityRole="button"
                accessibilityLabel="Activar acceso a notificaciones"
              >
                <Text style={styles.activateBtnText}>Activar</Text>
              </Pressable>
            )}
          </View>
        </View>
      )}

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, largeText && styles.sectionTitleLarge]}>Cuenta</Text>
        <Pressable
          style={styles.logoutBtn}
          onPress={handleLogout}
          accessibilityRole="button"
          accessibilityLabel="Cerrar sesión"
        >
          <MaterialIcons name="logout" size={largeText ? 24 : 20} color={colors.alert} />
          <Text style={[styles.logoutText, largeText && styles.logoutTextLarge]}>Cerrar sesión</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 24,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  title: {
    fontSize: 20,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  titleLarge: { fontSize: 26 },
  section: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 12,
  },
  sectionTitleLarge: { fontSize: 16 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  rowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  dot: { width: 10, height: 10, borderRadius: 5, flexShrink: 0 },
  rowLabel: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  rowLabelLarge: { fontSize: 20 },
  rowSub: { fontSize: 13, color: colors.primary, opacity: 0.55, marginTop: 1 },
  divider: { height: 1, backgroundColor: colors.primary, opacity: 0.08, marginVertical: 2 },
  activateBtn: {
    backgroundColor: colors.primary,
    borderRadius: 6,
    paddingVertical: 6,
    paddingHorizontal: 14,
    marginLeft: 8,
  },
  activateBtnText: { color: colors.white, fontSize: 13, fontWeight: fontWeight.bold },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
  },
  logoutText: {
    fontSize: fontSize.body,
    color: colors.alert,
    fontWeight: fontWeight.bold,
  },
  logoutTextLarge: { fontSize: 20 },
});
