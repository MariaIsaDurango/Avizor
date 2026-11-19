import { useState } from 'react';
import { View, Text, Image, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import { authStyles as a } from '../../styles/auth';
import { register } from '../../services/auth';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorRegister'>;

export default function TutorRegisterScreen({ navigation }: Props) {
  const [name, setName]                     = useState('');
  const [email, setEmail]                   = useState('');
  const [password, setPassword]             = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword]     = useState(false);
  const [showConfirm, setShowConfirm]       = useState(false);
  const [loading, setLoading]               = useState(false);
  const [error, setError]                   = useState<string | null>(null);

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
      await register({ display_name: name, email, password });
      navigation.navigate('VerifyEmail', { email });
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
          <Text style={a.brandName}>Avizor</Text>
        </View>

        <Text style={a.heading}>Crear cuenta de Tutor</Text>
        <Text style={a.subtitle}>Protege a quienes más quieres desde la app.</Text>

        {error && (
          <View style={a.alertError}>
            <Text style={a.alertErrorText}>{error}</Text>
          </View>
        )}

        <View style={a.formGroup}>
          <Text style={a.label}>Nombre</Text>
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
          <Text style={a.label}>Confirmar contraseña</Text>
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

        {loading
          ? <ActivityIndicator color="#164E55" size="large" style={{ marginVertical: 8 }} />
          : (
            <Pressable
              style={({ pressed }) => [a.submitBtn, pressed && a.submitBtnDisabled]}
              onPress={handleRegister}
              accessibilityRole="button"
              accessibilityLabel="Crear cuenta"
            >
              <Text style={a.submitText}>Crear cuenta</Text>
            </Pressable>
          )
        }

        <Pressable onPress={() => navigation.navigate('TutorLogin')} style={a.footerLink} accessibilityRole="link">
          <Text style={a.footerText}>¿Ya tienes cuenta? <Text style={a.footerTextBold}>Inicia sesión</Text></Text>
        </Pressable>

    </Screen>
  );
}
