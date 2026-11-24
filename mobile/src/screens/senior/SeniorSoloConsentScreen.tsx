import { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { STORAGE_KEYS, CONSENT_TEXT_VERSION } from '../../constants/storage';
import { apiFetch } from '../../services/api';
import { getMe } from '../../services/auth';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorSoloConsent'>;

const ANALYZED_ITEMS = [
  { icon: 'sms'          as const, label: 'SMS recibidos' },
  { icon: 'notifications' as const, label: 'Notificaciones de apps' },
  { icon: 'email'        as const, label: 'Emails abiertos en Gmail u Outlook' },
];

export default function SeniorSoloConsentScreen({ navigation }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  async function handleAccept() {
    setLoading(true);
    setError(null);
    try {
      const me = await getMe();
      const response = await apiFetch('/api/v1/consents', {
        method: 'POST',
        body: JSON.stringify({
          senior_id: me.id,
          type: 'self',
          scope: ['sms', 'notification', 'screen'],
          text_version: CONSENT_TEXT_VERSION,
          granted_by: me.id,
          granted_at: new Date().toISOString(),
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail ?? 'No se pudo registrar el consentimiento.');
      }
      await SecureStore.setItemAsync(STORAGE_KEYS.CONSENT_GIVEN, 'true');
      navigation.reset({ index: 0, routes: [{ name: 'SeniorHome' }] });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al guardar el consentimiento. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <MaterialIcons name="shield" size={64} color={colors.primary} style={styles.icon} />

        <Text style={styles.title}>Activa tu protección</Text>
        <Text style={styles.subtitle}>
          Para detectar fraudes automáticamente, Avizor necesita analizar el contenido de:
        </Text>

        <View style={styles.list}>
          {ANALYZED_ITEMS.map((item) => (
            <View key={item.label} style={styles.listItem}>
              <MaterialIcons name={item.icon} size={22} color={colors.primary} style={{ opacity: 0.7 }} />
              <Text style={styles.listLabel}>{item.label}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.note}>
          El texto se analiza en el momento y no se almacena. Puedes retirar este consentimiento en cualquier momento desde Ajustes.
        </Text>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {loading
          ? <ActivityIndicator size="large" color={colors.primary} style={styles.btn} />
          : (
            <Pressable
              style={({ pressed }) => [styles.btn, pressed && styles.btnPressed]}
              onPress={handleAccept}
              accessibilityRole="button"
              accessibilityLabel="Acepto y activo la protección"
            >
              <Text style={styles.btnText}>Acepto — activar protección</Text>
            </Pressable>
          )
        }
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    paddingVertical: 32,
    alignItems: 'center',
    gap: 20,
  },
  icon: { opacity: 0.9 },
  title: {
    fontSize: 24,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.75,
    textAlign: 'center',
    lineHeight: 22,
  },
  list: {
    width: '100%',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    gap: 14,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  listLabel: {
    fontSize: fontSize.body,
    color: colors.primary,
    fontWeight: fontWeight.bold,
  },
  note: {
    fontSize: 13,
    color: colors.primary,
    opacity: 0.55,
    textAlign: 'center',
    lineHeight: 19,
  },
  errorBox: {
    backgroundColor: '#FEE2E2',
    borderRadius: 8,
    padding: 12,
    width: '100%',
  },
  errorText: {
    color: colors.alert,
    fontSize: fontSize.body,
    textAlign: 'center',
  },
  btn: {
    width: '100%',
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 18,
    alignItems: 'center',
    marginTop: 8,
  },
  btnPressed: { opacity: 0.8 },
  btnText: {
    color: colors.white,
    fontWeight: fontWeight.bold,
    fontSize: fontSize.body,
  },
});
