import { useState, useEffect } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { createPairing, AccessibilityProfile } from '../../services/pairing';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorPairing'>;

const ACCESSIBILITY_OPTIONS: { key: keyof AccessibilityProfile; label: string }[] = [
  { key: 'color_blindness',    label: 'Daltonismo' },
  { key: 'low_vision',         label: 'Baja visión' },
  { key: 'blindness',          label: 'Ceguera' },
  { key: 'hearing_impairment', label: 'Dificultad auditiva' },
];

const EMPTY_PROFILE: AccessibilityProfile = {
  color_blindness: false,
  low_vision: false,
  blindness: false,
  hearing_impairment: false,
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function formatCode(code: string): string {
  return `${code.slice(0, 3)} ${code.slice(3)}`;
}

export default function TutorPairingScreen({ navigation }: Props) {
  const [seniorName, setSeniorName] = useState('');
  const [guardianPhone, setGuardianPhone] = useState('');
  const [profile, setProfile] = useState<AccessibilityProfile>(EMPTY_PROFILE);
  const [code, setCode] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!expiresAt) return;
    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));
      setSecondsLeft(remaining);
      if (remaining === 0) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  function toggleProfile(key: keyof AccessibilityProfile) {
    setProfile((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const hasProfile = Object.values(profile).some(Boolean);

  async function handleGenerate() {
    if (!seniorName.trim()) {
      setError('Ingresa el nombre del Sénior.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const pairing = await createPairing(
        seniorName.trim(),
        hasProfile ? profile : undefined,
        guardianPhone.trim() || undefined,
      );
      const expiry = new Date(pairing.expires_at);
      setCode(pairing.code);
      setExpiresAt(expiry);
      setSecondsLeft(Math.floor((expiry.getTime() - Date.now()) / 1000));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error desconocido.');
    } finally {
      setLoading(false);
    }
  }

  const isExpired = expiresAt !== null && secondsLeft === 0;

  return (
    <Screen scrollable style={styles.screen}>
      <View style={styles.top}>
        <Text style={styles.title}>Vincular dispositivo Sénior</Text>
        <Text style={styles.subtitle}>
          Genera un código y compártelo con el Sénior para vincularlo a tu cuenta.
        </Text>
      </View>

      <View style={styles.middle}>
        {loading && <ActivityIndicator size="large" color={colors.primary} />}
        {error !== null && <Text style={styles.error}>{error}</Text>}

        {!loading && code === null && (
          <>
            <TextInput
              style={styles.input}
              placeholder="Nombre del Sénior"
              placeholderTextColor={colors.primary}
              value={seniorName}
              onChangeText={(v) => { setSeniorName(v); setError(null); }}
              maxLength={50}
              autoCapitalize="words"
              autoComplete="name"
            />

            <TextInput
              style={styles.input}
              placeholder="Tu teléfono (opcional) — p.ej. +34 600 000 000"
              placeholderTextColor={colors.primary}
              value={guardianPhone}
              onChangeText={setGuardianPhone}
              keyboardType="phone-pad"
              autoComplete="tel"
              accessibilityLabel="Tu número de teléfono"
              accessibilityHint="El Sénior podrá llamarte desde la app si detecta algo peligroso"
            />

            <View style={styles.accessibilitySection}>
              <Text style={styles.accessibilityTitle}>
                Perfil de accesibilidad{' '}
                <Text style={styles.accessibilityOptional}>(opcional)</Text>
              </Text>
              <Text style={styles.accessibilityHint}>
                La app del Sénior adaptará su interfaz según estas necesidades.
              </Text>
              {ACCESSIBILITY_OPTIONS.map(({ key, label }) => (
                <Pressable
                  key={key}
                  style={styles.checkRow}
                  onPress={() => toggleProfile(key)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: profile[key] }}
                  accessibilityLabel={label}
                >
                  <View style={[styles.checkbox, profile[key] && styles.checkboxChecked]}>
                    {profile[key] && (
                      <MaterialIcons name="check" size={16} color={colors.white} />
                    )}
                  </View>
                  <Text style={styles.checkLabel}>{label}</Text>
                </Pressable>
              ))}
            </View>
          </>
        )}

        {!loading && code !== null && !isExpired && (
          <>
            <Text style={styles.codeLabel}>Código de vinculación</Text>
            <Text style={styles.code} accessibilityLabel={`Código: ${code.split('').join(' ')}`}>
              {formatCode(code)}
            </Text>
            <Text style={styles.countdown}>Expira en {formatTime(secondsLeft)}</Text>
            <Text style={styles.hint}>
              El Sénior debe ingresar este código en su aplicación Avizor.
            </Text>
          </>
        )}

        {!loading && isExpired && (
          <Text style={styles.expired}>El código ha expirado. Genera uno nuevo.</Text>
        )}
      </View>

      <View style={styles.footer}>
        {(!code || isExpired) && !loading && (
          <Button
            label={isExpired ? 'Generar nuevo código' : 'Generar código'}
            onPress={handleGenerate}
          />
        )}
        {code !== null && !isExpired && (
          <Button
            label="Continuar al panel"
            variant="action"
            onPress={() => navigation.reset({ index: 0, routes: [{ name: 'TutorDashboard' }] })}
          />
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingBottom: 40,
  },
  top: {
    marginTop: 24,
    gap: 8,
  },
  middle: {
    gap: 16,
    width: '100%',
    marginTop: 24,
  },
  footer: {
    gap: 12,
    marginTop: 24,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
    opacity: 0.7,
  },
  input: {
    width: '100%',
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 8,
    padding: 14,
    fontSize: fontSize.body,
    color: colors.primary,
    backgroundColor: colors.white,
  },
  accessibilitySection: {
    backgroundColor: colors.white,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: colors.primary,
    padding: 16,
    gap: 10,
  },
  accessibilityTitle: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  accessibilityOptional: {
    fontWeight: '400',
    opacity: 0.6,
  },
  accessibilityHint: {
    fontSize: 13,
    color: colors.primary,
    opacity: 0.6,
    marginBottom: 4,
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 4,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.white,
  },
  checkboxChecked: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  checkLabel: {
    fontSize: fontSize.body,
    color: colors.primary,
  },
  codeLabel: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  code: {
    fontSize: 56,
    fontWeight: fontWeight.bold,
    color: colors.deep,
    letterSpacing: 8,
  },
  countdown: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.warning,
  },
  hint: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
    opacity: 0.7,
    marginTop: 8,
  },
  expired: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.alert,
    textAlign: 'center',
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
  },
});
