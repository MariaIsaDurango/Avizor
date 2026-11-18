import { useState } from 'react';
import { View, Text, Image, TextInput, Pressable, ActivityIndicator, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import { authStyles as a } from '../../styles/auth';
import { login, EmailNotVerifiedError } from '../../services/auth';
import { registerDevice } from '../../services/devices';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorLogin'>;

export default function TutorLoginScreen({ navigation, route }: Props) {
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
      registerDevice().catch((e) => { if (__DEV__) console.warn('[devices] registerDevice failed:', e); });
      navigation.reset({ index: 0, routes: [{ name: 'TutorDashboard' }] });
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
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>

        <Pressable onPress={() => navigation.navigate('ModeSelection')} style={a.back} accessibilityRole="button" accessibilityLabel="Volver">
          <Ionicons name="arrow-back-outline" size={18} color="#6b7280" />
          <Text style={a.backText}>Volver</Text>
        </Pressable>

        <View style={a.brand}>
          <Image source={require('../../../assets/logo-web.png')} style={a.logo} resizeMode="contain" accessibilityLabel="" />
          <Text style={a.brandName}>Avizor</Text>
        </View>

        <Text style={a.heading}>Bienvenido de nuevo</Text>
        <Text style={a.subtitle}>Inicia sesión para acceder al panel de Tutor.</Text>

        {error && (
          <View style={a.alertError}>
            <Text style={a.alertErrorText}>{error}</Text>
          </View>
        )}

        <View style={a.formGroup}>
          <Text style={a.label}>Email</Text>
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
          <Text style={a.label}>Contraseña</Text>
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
              <Text style={a.submitText}>Iniciar sesión</Text>
            </Pressable>
          )
        }

        <Pressable onPress={() => navigation.navigate('TutorRegister')} style={a.footerLink} accessibilityRole="link">
          <Text style={a.footerText}>¿No tienes cuenta? <Text style={a.footerTextBold}>Regístrate</Text></Text>
        </Pressable>

      </KeyboardAvoidingView>
    </Screen>
  );
}
