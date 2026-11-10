import { useState } from 'react';
import { View, Text, TextInput, StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Pressable } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { register } from '../../services/auth';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorRegister'>;

export default function TutorRegisterScreen({ navigation }: Props) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRegister() {
    if (!name || !email || !password || !confirmPassword) {
      setError('Completa todos los campos.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await register({ name, email, password });
      navigation.reset({ index: 0, routes: [{ name: 'TutorDashboard' }] });
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Error al registrarse.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen scrollable>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <Text style={styles.title}>Crear cuenta</Text>

        <TextInput
          style={styles.input}
          placeholder="Nombre"
          placeholderTextColor={colors.primary}
          value={name}
          onChangeText={(v) => { setName(v); setError(null); }}
          autoComplete="name"
        />

        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor={colors.primary}
          value={email}
          onChangeText={(v) => { setEmail(v); setError(null); }}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
        />

        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          placeholderTextColor={colors.primary}
          value={password}
          onChangeText={(v) => { setPassword(v); setError(null); }}
          secureTextEntry
          autoComplete="new-password"
        />

        <TextInput
          style={styles.input}
          placeholder="Confirmar contraseña"
          placeholderTextColor={colors.primary}
          value={confirmPassword}
          onChangeText={(v) => { setConfirmPassword(v); setError(null); }}
          secureTextEntry
          autoComplete="new-password"
        />

        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.buttonWrapper}>
          {loading
            ? <ActivityIndicator color={colors.primary} size="large" />
            : <Button label="Crear cuenta" onPress={handleRegister} />
          }
        </View>

        <Pressable
          onPress={() => navigation.navigate('TutorLogin')}
          accessibilityRole="link"
          style={styles.link}
        >
          <Text style={styles.linkText}>¿Ya tienes cuenta? Inicia sesión</Text>
        </Pressable>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 32,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: 8,
    padding: 14,
    fontSize: fontSize.body,
    color: colors.primary,
    backgroundColor: colors.white,
    marginBottom: 16,
  },
  error: {
    color: colors.alert,
    fontSize: fontSize.body,
    marginBottom: 16,
    textAlign: 'center',
  },
  buttonWrapper: {
    marginTop: 8,
    marginBottom: 16,
  },
  link: { alignItems: 'center', marginTop: 8 },
  linkText: {
    fontSize: fontSize.body,
    color: colors.primary,
    textDecorationLine: 'underline',
  },
});
