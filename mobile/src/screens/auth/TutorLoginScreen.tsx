import { useState } from 'react';
import { View, Text, Image, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import { authStyles as a } from '../../styles/auth';
import * as SecureStore from 'expo-secure-store';
import { login, EmailNotVerifiedError } from '../../services/auth';
import { registerDevice } from '../../services/devices';
import { STORAGE_KEYS } from '../../constants/storage';
import { RootStackParamList } from '../../navigation/types';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorLogin'>;

export default function TutorLoginScreen({ navigation, route }: Props) {
  const { largeText } = useAccessibility();
  const [email, setEmail]           = useState(route.params?.email ?? '');
  const [password, setPassword]     = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);

  async function handleLogin() {
    if (!email || !password) { setError('Completa todos los campos.'); return; }
    setLoading(true);
    setError(null);
    try {
      await login({ email, password });
      const mode = await SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE);
      if (mode === 'senior_solo') {
        const [consentGiven, consentSkipped] = await Promise.all([
          SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
          SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_SKIPPED),
        ]);
        const withinSkipWindow = consentSkipped
          ? Date.now() - Number(consentSkipped) < 7 * 24 * 60 * 60 * 1000
          : false;
        const hasConsent = consentGiven === 'true' || withinSkipWindow;
        navigation.reset({ index: 0, routes: [{ name: hasConsent ? 'SeniorHome' : 'SeniorSoloConsent' }] });
      } else {
        registerDevice().catch((e) => { if (__DEV__) console.warn('[devices] registerDevice failed:', e); });
        navigation.reset({ index: 0, routes: [{ name: 'TutorDashboard' }] });
      }
    } catch (e) {
      if (e instanceof EmailNotVerifiedError) {
        navigation.navigate('VerifyEmail', { email: e.email });
      } else {
        setError('Credenciales incorrectas. Verifica tu email y contraseña.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen scrollable>
        <Pressable onPress={() => navigation.navigate('ModeSelection')} style={a.back} accessibilityRole="button" accessibilityLabel="Volver">
          <Ionicons name="arrow-back-outline" size={18} color="#6b7280" />
          <Text style={a.backText}>Volver</Text>
        </Pressable>

        <View style={a.brand}>
          <Image source={require('../../../assets/logo-web.png')} style={a.logo} resizeMode="contain" accessibilityLabel="" />
          <Text style={[a.brandName, largeText && { fontSize: 26 }]}>Avizor</Text>
        </View>

        <Text style={[a.heading, largeText && { fontSize: 26 }]}>Bienvenido de nuevo</Text>
        <Text style={[a.subtitle, largeText && { fontSize: 18 }]}>Inicia sesión para acceder a tu cuenta.</Text>

        {error && (
          <View style={a.alertError}>
            <Text style={a.alertErrorText}>{error}</Text>
          </View>
        )}

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
              placeholder="Tu contraseña"
              placeholderTextColor="#aaa"
              value={password}
              onChangeText={(v) => { setPassword(v); setError(null); }}
              secureTextEntry={!showPassword}
              autoComplete="current-password"
            />
            <Pressable onPress={() => setShowPassword(v => !v)} style={a.eyeBtn} accessibilityLabel={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
              <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={20} color="#888" />
            </Pressable>
          </View>
        </View>

        {loading
          ? <ActivityIndicator color="#164E55" size="large" style={{ marginVertical: 8 }} />
          : (
            <Pressable
              style={({ pressed }) => [a.submitBtn, pressed && a.submitBtnDisabled]}
              onPress={handleLogin}
              accessibilityRole="button"
              accessibilityLabel="Iniciar sesión"
            >
              <Text style={[a.submitText, largeText && { fontSize: 19 }]}>Iniciar sesión</Text>
            </Pressable>
          )
        }

        <Pressable onPress={() => navigation.navigate('TutorRegister')} style={a.footerLink} accessibilityRole="link">
          <Text style={[a.footerText, largeText && { fontSize: 17 }]}>¿No tienes cuenta? <Text style={[a.footerTextBold, largeText && { fontSize: 17 }]}>Regístrate</Text></Text>
        </Pressable>

    </Screen>
  );
}
