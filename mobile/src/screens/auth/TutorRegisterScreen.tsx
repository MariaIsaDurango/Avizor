import { useState } from 'react';
import { View, Text, Image, TextInput, Pressable, ActivityIndicator, StyleSheet, Switch, Linking } from 'react-native';

const PRIVACY_URL = 'https://avizor-production.up.railway.app/privacidad';
import { Ionicons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import { authStyles as a } from '../../styles/auth';
import { register, registerSeniorSolo } from '../../services/auth';
import { STORAGE_KEYS } from '../../constants/storage';
import { RootStackParamList } from '../../navigation/types';
import { colors } from '../../constants/colors';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorRegister'>;
type Role = 'tutor' | 'senior_solo';

interface A11yState {
  colorBlind: boolean;
  largeText: boolean;
  hardOfHearing: boolean;
}

export default function TutorRegisterScreen({ navigation }: Props) {
  const { largeText } = useAccessibility();
  const [role, setRole]                       = useState<Role>('tutor');
  const [name, setName]                       = useState('');
  const [email, setEmail]                     = useState('');
  const [password, setPassword]               = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword]       = useState(false);
  const [showConfirm, setShowConfirm]         = useState(false);
  const [a11y, setA11y]                       = useState<A11yState>({ colorBlind: false, largeText: false, hardOfHearing: false });
  const [loading, setLoading]                 = useState(false);
  const [error, setError]                     = useState<string | null>(null);

  function toggleA11y(key: keyof A11yState) {
    setA11y(prev => ({ ...prev, [key]: !prev[key] }));
  }

  async function handleRegister() {
    if (!name || !email || !password || !confirmPassword) {
      setError('Completa todos los campos.');
      return;
    }
    if (password.length < 10) {
      setError('La contraseña debe tener al menos 10 caracteres.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (role === 'senior_solo') {
        await registerSeniorSolo({ display_name: name, email, password });
        await SecureStore.setItemAsync(
          STORAGE_KEYS.ACCESSIBILITY_PROFILE,
          JSON.stringify({
            color_blindness: a11y.colorBlind,
            low_vision: a11y.largeText,
            blindness: false,
            hearing_impairment: a11y.hardOfHearing,
          }),
        );
        navigation.navigate('VerifyEmail', { email, flow: 'senior_solo' });
      } else {
        await register({ display_name: name, email, password });
        navigation.navigate('VerifyEmail', { email });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al registrarse.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen scrollable>
      <Pressable onPress={() => navigation.goBack()} style={a.back} accessibilityRole="button" accessibilityLabel="Volver">
        <Ionicons name="arrow-back-outline" size={18} color="#6b7280" />
        <Text style={a.backText}>Volver</Text>
      </Pressable>

      <View style={a.brand}>
        <Image source={require('../../../assets/logo-web.png')} style={a.logo} resizeMode="contain" accessibilityLabel="" />
        <Text style={[a.brandName, largeText && { fontSize: 26 }]}>Avizor</Text>
      </View>

      <Text style={[a.heading, largeText && { fontSize: 26 }]}>Crear cuenta</Text>
      <Text style={[a.subtitle, largeText && { fontSize: 18 }]}>¿Para quién es la app?</Text>

      <View style={s.toggle}>
        <Pressable
          style={[s.pill, role === 'senior_solo' && s.pillActive]}
          onPress={() => setRole('senior_solo')}
          accessibilityRole="button"
          accessibilityLabel="Para mí"
        >
          <Text style={[s.pillText, role === 'senior_solo' && s.pillTextActive, largeText && { fontSize: 18 }]}>Para mí</Text>
        </Pressable>
        <Pressable
          style={[s.pill, role === 'tutor' && s.pillActive]}
          onPress={() => setRole('tutor')}
          accessibilityRole="button"
          accessibilityLabel="Para un familiar"
        >
          <Text style={[s.pillText, role === 'tutor' && s.pillTextActive, largeText && { fontSize: 18 }]}>Para un familiar</Text>
        </Pressable>
      </View>

      {error && (
        <View style={a.alertError}>
          <Text style={a.alertErrorText}>{error}</Text>
        </View>
      )}

      <View style={a.formGroup}>
        <Text style={[a.label, largeText && { fontSize: 17 }]}>Nombre</Text>
        <TextInput
          style={a.input}
          placeholder="Tu nombre"
          placeholderTextColor="#aaa"
          value={name}
          onChangeText={(v) => { setName(v); setError(null); }}
          autoComplete="name"
          autoCapitalize="words"
        />
      </View>

      <View style={a.formGroup}>
        <Text style={[a.label, largeText && { fontSize: 17 }]}>Email</Text>
        <TextInput
          style={a.input}
          placeholder="correo@ejemplo.com"
          placeholderTextColor="#aaa"
          value={email}
          onChangeText={(v) => { setEmail(v); setError(null); }}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
        />
      </View>

      <View style={a.formGroup}>
        <Text style={[a.label, largeText && { fontSize: 17 }]}>Contraseña</Text>
        <View style={a.inputWrap}>
          <TextInput
            style={[a.input, a.inputWithEye]}
            placeholder="Mínimo 10 caracteres"
            placeholderTextColor="#aaa"
            value={password}
            onChangeText={(v) => { setPassword(v); setError(null); }}
            secureTextEntry={!showPassword}
            autoComplete="new-password"
          />
          <Pressable onPress={() => setShowPassword(v => !v)} style={a.eyeBtn} accessibilityLabel={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
            <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={20} color="#888" />
          </Pressable>
        </View>
        <Text style={a.hint}>Al menos 10 caracteres.</Text>
      </View>

      <View style={a.formGroup}>
        <Text style={[a.label, largeText && { fontSize: 17 }]}>Confirmar contraseña</Text>
        <View style={a.inputWrap}>
          <TextInput
            style={[a.input, a.inputWithEye]}
            placeholder="Repite la contraseña"
            placeholderTextColor="#aaa"
            value={confirmPassword}
            onChangeText={(v) => { setConfirmPassword(v); setError(null); }}
            secureTextEntry={!showConfirm}
            autoComplete="new-password"
          />
          <Pressable onPress={() => setShowConfirm(v => !v)} style={a.eyeBtn} accessibilityLabel={showConfirm ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
            <Ionicons name={showConfirm ? 'eye-off-outline' : 'eye-outline'} size={20} color="#888" />
          </Pressable>
        </View>
      </View>

      {role === 'senior_solo' && (
        <View style={s.a11ySection}>
          <Text style={s.a11yTitle}>Accesibilidad</Text>

          <View style={s.a11yRow}>
            <View style={s.a11yRowLeft}>
              <Ionicons name="color-palette-outline" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
              <Text style={[s.a11yLabel, largeText && { fontSize: 19 }]}>Daltonismo</Text>
            </View>
            <Switch
              value={a11y.colorBlind}
              onValueChange={() => toggleA11y('colorBlind')}
              trackColor={{ false: '#d1d5db', true: colors.primary }}
              thumbColor="#fff"
              accessibilityLabel="Daltonismo"
            />
          </View>

          <View style={s.divider} />

          <View style={s.a11yRow}>
            <View style={s.a11yRowLeft}>
              <Ionicons name="text-outline" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
              <Text style={[s.a11yLabel, largeText && { fontSize: 19 }]}>Texto grande</Text>
            </View>
            <Switch
              value={a11y.largeText}
              onValueChange={() => toggleA11y('largeText')}
              trackColor={{ false: '#d1d5db', true: colors.primary }}
              thumbColor="#fff"
              accessibilityLabel="Texto grande"
            />
          </View>

          <View style={s.divider} />

          <View style={s.a11yRow}>
            <View style={s.a11yRowLeft}>
              <Ionicons name="ear-outline" size={20} color={colors.primary} style={{ opacity: 0.7 }} />
              <Text style={[s.a11yLabel, largeText && { fontSize: 19 }]}>Dificultad para escuchar</Text>
            </View>
            <Switch
              value={a11y.hardOfHearing}
              onValueChange={() => toggleA11y('hardOfHearing')}
              trackColor={{ false: '#d1d5db', true: colors.primary }}
              thumbColor="#fff"
              accessibilityLabel="Dificultad para escuchar"
            />
          </View>

          <View style={s.talkbackBanner} accessibilityRole="text">
            <Ionicons name="mic-outline" size={18} color={colors.primary} style={{ opacity: 0.8 }} />
            <View style={s.talkbackTextBlock}>
              <Text style={s.talkbackTitle}>Compatible con TalkBack</Text>
              <Text style={s.talkbackDesc}>
                Si usas el lector de pantalla de Android, Avizor lo detecta automáticamente y se adapta.
              </Text>
            </View>
          </View>
        </View>
      )}

      {loading
        ? <ActivityIndicator color="#164E55" size="large" style={{ marginVertical: 8 }} />
        : (
          <Pressable
            style={({ pressed }) => [a.submitBtn, pressed && a.submitBtnDisabled]}
            onPress={handleRegister}
            accessibilityRole="button"
            accessibilityLabel="Crear cuenta"
          >
            <Text style={[a.submitText, largeText && { fontSize: 19 }]}>Crear cuenta</Text>
          </Pressable>
        )
      }

      <Text style={[a.footerText, { textAlign: 'center', marginBottom: 8 }, largeText && { fontSize: 15 }]}>
        Al crear tu cuenta aceptas nuestra{' '}
        <Text
          style={[a.footerTextBold, { color: colors.primary }]}
          onPress={() => Linking.openURL(PRIVACY_URL)}
          accessibilityRole="link"
          accessibilityLabel="Política de privacidad"
        >
          política de privacidad
        </Text>
        {'. '}Responsable: <Text style={a.footerTextBold}>Avizor</Text>.
      </Text>

      <Pressable onPress={() => navigation.navigate('TutorLogin')} style={a.footerLink} accessibilityRole="link">
        <Text style={[a.footerText, largeText && { fontSize: 17 }]}>¿Ya tienes cuenta? <Text style={[a.footerTextBold, largeText && { fontSize: 17 }]}>Inicia sesión</Text></Text>
      </Pressable>
    </Screen>
  );
}

const s = StyleSheet.create({
  toggle: {
    flexDirection: 'row',
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: colors.primary,
    overflow: 'hidden',
    marginBottom: 20,
  },
  pill: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  pillActive: {
    backgroundColor: colors.primary,
  },
  pillText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  pillTextActive: {
    color: '#fff',
  },
  a11ySection: {
    backgroundColor: colors.white,
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  a11yTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.primary,
    opacity: 0.55,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 10,
  },
  a11yRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  a11yRowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flex: 1,
  },
  a11yLabel: {
    fontSize: 15,
    color: colors.primary,
    fontWeight: '500',
  },
  talkbackBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginTop: 12,
    backgroundColor: '#EAF2F3',
    borderRadius: 8,
    padding: 12,
  },
  talkbackTextBlock: {
    flex: 1,
    gap: 2,
  },
  talkbackTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  talkbackDesc: {
    fontSize: 13,
    color: colors.primary,
    opacity: 0.7,
    lineHeight: 18,
  },
  divider: {
    height: 1,
    backgroundColor: colors.primary,
    opacity: 0.07,
  },
});
