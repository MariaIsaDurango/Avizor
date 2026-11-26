import { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, Switch, StyleSheet, Alert, AppState, Platform, NativeModules, Linking } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS } from '../../constants/storage';
import { apiFetch, clearToken } from '../../services/api';
import { deleteAccount } from '../../services/auth';
import { useAccessibility } from '../../contexts/AccessibilityContext';
import { RootStackParamList } from '../../navigation/types';

const SUPPORT_URL = 'https://avizor-production.up.railway.app/support';

const { AvizorNotification, AvizorAccessibility } = NativeModules;

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorSettings'>;

export default function SeniorSettingsScreen({ navigation }: Props) {
  const { largeText } = useAccessibility();
  const [isSeniorSolo, setIsSeniorSolo] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [notifEnabled, setNotifEnabled] = useState<boolean | null>(null);
  const [a11yEnabled, setA11yEnabled] = useState<boolean | null>(null);
  const [showDeleteForm, setShowDeleteForm] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const appState = useRef(AppState.currentState);

  function checkPermissions() {
    AvizorNotification?.isServiceEnabled().then(setNotifEnabled).catch(() => setNotifEnabled(false));
    AvizorAccessibility?.isServiceEnabled().then(setA11yEnabled).catch(() => setA11yEnabled(false));
  }

  useEffect(() => {
    Promise.all([
      SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
      SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
      SecureStore.getItemAsync(STORAGE_KEYS.TTS_ENABLED),
    ])
      .then(([mode, consent, tts]) => {
        setIsSeniorSolo(mode === 'senior_solo');
        setConsentGiven(consent === 'true');
        setTtsEnabled(tts === 'true');
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    checkPermissions();
    const sub = AppState.addEventListener('change', (next) => {
      if (appState.current?.match(/inactive|background/) && next === 'active') checkPermissions();
      appState.current = next;
    });
    return () => sub.remove();
  }, []);

  function handleRevokeConsent() {
    Alert.alert(
      'Retirar consentimiento',
      'Se desactivará el análisis automático de mensajes. Podrás volver a activarlo cuando quieras.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Retirar',
          style: 'destructive',
          onPress: async () => {
            try {
              const consentId = await SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_ID);
              const endpoint = consentId
                ? `/api/v1/consents/${consentId}/revoke`
                : '/api/v1/consents/me/revoke';
              const response = await apiFetch(endpoint, { method: 'POST' });
              if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                Alert.alert('Error', err.detail ?? 'No se pudo retirar el consentimiento. Inténtalo más tarde.');
                return;
              }
            } catch {
              Alert.alert('Error', 'No se pudo retirar el consentimiento. Inténtalo más tarde.');
              return;
            }
            await Promise.allSettled([
              SecureStore.deleteItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
              SecureStore.deleteItemAsync(STORAGE_KEYS.CONSENT_ID),
              SecureStore.deleteItemAsync(STORAGE_KEYS.CONSENT_SKIPPED),
            ]);
            navigation.reset({ index: 0, routes: [{ name: 'SeniorSoloConsent' }] });
          },
        },
      ],
    );
  }

  async function handleDeleteAccount() {
    if (!deletePassword.trim()) { setDeleteError('Introduce tu contraseña.'); return; }
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteAccount(deletePassword);
      await clearToken();
      await Promise.allSettled(
        Object.values(STORAGE_KEYS).map(k => SecureStore.deleteItemAsync(k)),
      );
      navigation.reset({ index: 0, routes: [{ name: 'Welcome' }] });
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : 'No se pudo eliminar la cuenta.');
      setDeleting(false);
    }
  }

  function handleLogout() {
    Alert.alert(
      '¿Estás seguro?',
      isSeniorSolo
        ? 'Necesitarás tu email y contraseña para volver a entrar.'
        : 'Necesitarás un nuevo código de tu familiar para volver a entrar.',
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

  function handleToggleTts(val: boolean) {
    setTtsEnabled(val);
    SecureStore.setItemAsync(STORAGE_KEYS.TTS_ENABLED, String(val)).catch(() => {});
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
                onPress={() => Alert.alert(
                  'Activar alertas',
                  'Se abrirán los ajustes del sistema. Busca "Avizor" en la lista y actívalo.',
                  [
                    { text: 'Cancelar', style: 'cancel' },
                    { text: 'Ir a ajustes', onPress: () => AvizorNotification?.openSettings() },
                  ],
                )}
                accessibilityRole="button"
                accessibilityLabel="Activar acceso a notificaciones"
              >
                <Text style={styles.activateBtnText}>Activar</Text>
              </Pressable>
            )}
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <View style={[styles.dot, { backgroundColor: dotColor(a11yEnabled), opacity: dotOpacity(a11yEnabled) }]} />
              <View>
                <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Análisis de emails</Text>
                <Text style={styles.rowSub}>
                  {a11yEnabled === null ? 'Comprobando…' : a11yEnabled ? 'Activo' : 'Inactivo'}
                </Text>
              </View>
            </View>
            {a11yEnabled === false && (
              <Pressable
                style={styles.activateBtn}
                onPress={() => Alert.alert(
                  'Activar análisis de emails',
                  'Se abrirán los ajustes de accesibilidad. Busca "Avizor" y actívalo para que pueda revisar tus emails automáticamente.',
                  [
                    { text: 'Cancelar', style: 'cancel' },
                    { text: 'Ir a ajustes', onPress: () => AvizorAccessibility?.openSettings() },
                  ],
                )}
                accessibilityRole="button"
                accessibilityLabel="Activar análisis automático de emails"
              >
                <Text style={styles.activateBtnText}>Activar</Text>
              </Pressable>
            )}
          </View>
        </View>
      )}

      {isSeniorSolo && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, largeText && styles.sectionTitleLarge]}>Actividad</Text>
          <Pressable
            style={styles.row}
            onPress={() => navigation.navigate('SeniorSoloAlerts')}
            accessibilityRole="button"
            accessibilityLabel="Ver panel de alertas"
          >
            <View style={styles.rowLeft}>
              <MaterialIcons name="notifications" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
              <View>
                <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Panel de alertas</Text>
                <Text style={styles.rowSub}>Revisa las alertas detectadas</Text>
              </View>
            </View>
            <MaterialIcons name="chevron-right" size={20} color={colors.primary} style={{ opacity: 0.4 }} />
          </Pressable>

          {consentGiven && (
            <>
              <View style={styles.divider} />
              <Pressable
                style={styles.row}
                onPress={handleRevokeConsent}
                accessibilityRole="button"
                accessibilityLabel="Retirar consentimiento de análisis automático"
              >
                <View style={styles.rowLeft}>
                  <MaterialIcons name="shield" size={20} color={colors.alert} style={{ opacity: 0.8 }} />
                  <View>
                    <Text style={[styles.rowLabel, { color: colors.alert }, largeText && styles.rowLabelLarge]}>
                      Retirar consentimiento
                    </Text>
                    <Text style={styles.rowSub}>Desactivar análisis automático</Text>
                  </View>
                </View>
              </Pressable>
            </>
          )}
        </View>
      )}

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, largeText && styles.sectionTitleLarge]}>Preferencias</Text>
        <View style={styles.row}>
          <View style={styles.rowLeft}>
            <MaterialIcons name="volume-up" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Leer alertas en voz alta</Text>
              <Text style={styles.rowSub}>El teléfono leerá el aviso cuando algo sea peligroso</Text>
            </View>
          </View>
          <Switch
            value={ttsEnabled}
            onValueChange={handleToggleTts}
            trackColor={{ false: '#d4d4d8', true: colors.primary }}
            thumbColor={colors.white}
            accessibilityLabel="Activar o desactivar lectura de alertas en voz alta"
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, largeText && styles.sectionTitleLarge]}>Ayuda</Text>
        <Pressable
          style={styles.row}
          onPress={() => Linking.openURL(SUPPORT_URL + (isSeniorSolo ? '#solo' : ''))}
          accessibilityRole="button"
          accessibilityLabel="Abrir centro de soporte"
        >
          <View style={styles.rowLeft}>
            <MaterialIcons name="help-outline" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
            <View>
              <Text style={[styles.rowLabel, largeText && styles.rowLabelLarge]}>Centro de soporte</Text>
              <Text style={styles.rowSub}>Guías y preguntas frecuentes</Text>
            </View>
          </View>
          <MaterialIcons name="open-in-new" size={16} color={colors.primary} style={{ opacity: 0.4 }} />
        </Pressable>
      </View>

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

        {isSeniorSolo && (
          <>
            <View style={styles.divider} />
            <Pressable
              style={styles.logoutBtn}
              onPress={() => { setShowDeleteForm(v => !v); setDeleteError(''); setDeletePassword(''); }}
              accessibilityRole="button"
              accessibilityLabel="Eliminar mi cuenta"
              accessibilityState={{ expanded: showDeleteForm }}
            >
              <MaterialIcons name="delete-forever" size={largeText ? 24 : 20} color={colors.alert} />
              <Text style={[styles.logoutText, largeText && styles.logoutTextLarge]}>Eliminar mi cuenta</Text>
            </Pressable>
            {showDeleteForm && (
              <View style={styles.deleteForm}>
                <Text style={[styles.deleteHint, largeText && styles.deleteHintLarge]}>
                  Se borrarán tu cuenta y todos tus datos. Esta acción no se puede deshacer.
                </Text>
                <TextInput
                  style={[styles.deleteInput, largeText && styles.deleteInputLarge]}
                  placeholder="Contraseña"
                  placeholderTextColor={colors.primary}
                  secureTextEntry
                  value={deletePassword}
                  onChangeText={t => { setDeletePassword(t); setDeleteError(''); }}
                  autoComplete="current-password"
                  accessibilityLabel="Contraseña para confirmar eliminación de cuenta"
                />
                {deleteError !== '' && (
                  <Text style={[styles.deleteError, largeText && styles.deleteErrorLarge]} accessibilityLiveRegion="assertive">{deleteError}</Text>
                )}
                <Pressable
                  style={[styles.deleteConfirmBtn, deleting && styles.deleteConfirmBtnDisabled]}
                  onPress={handleDeleteAccount}
                  disabled={deleting}
                  accessibilityRole="button"
                  accessibilityLabel="Confirmar eliminación de cuenta"
                >
                  <Text style={[styles.deleteConfirmText, largeText && styles.deleteConfirmTextLarge]}>
                    {deleting ? 'Eliminando…' : 'Confirmar eliminación'}
                  </Text>
                </Pressable>
              </View>
            )}
          </>
        )}
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
  deleteForm: { marginTop: 12, gap: 10 },
  deleteHint: { fontSize: 13, color: colors.alert, opacity: 0.8, lineHeight: 18 },
  deleteHintLarge: { fontSize: 17 },
  deleteInput: {
    borderWidth: 1.5,
    borderColor: colors.alert,
    borderRadius: 8,
    padding: 12,
    fontSize: fontSize.body,
    color: colors.primary,
  },
  deleteInputLarge: { fontSize: 20 },
  deleteError: { fontSize: 13, color: colors.alert },
  deleteErrorLarge: { fontSize: 17 },
  deleteConfirmBtn: {
    backgroundColor: colors.alert,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
  },
  deleteConfirmBtnDisabled: { opacity: 0.6 },
  deleteConfirmText: { color: colors.white, fontWeight: fontWeight.bold, fontSize: fontSize.body },
  deleteConfirmTextLarge: { fontSize: 20 },
});
