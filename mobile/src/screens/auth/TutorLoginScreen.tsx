import { useState } from 'react';
import { View, Text, TextInput, StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator, Pressable } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { login } from '../../services/auth';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorLogin'>;

export default function TutorLoginScreen({ navigation }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    if (!email || !password) {
      setError('Completa todos los campos.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login({ email, password });
      navigation.reset({ index: 0, routes: [{ name: 'TutorDashboard' }] });
    } catch {
      setError('Credenciales incorrectas. Verifica tu email y contraseña.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen scrollable>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <Text style={styles.title}>Iniciar sesión</Text>

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
          autoComplete="current-password"
        />

        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.buttonWrapper}>
          {loading
            ? <ActivityIndicator color={colors.primary} size="large" />
            : <Button label="Iniciar sesión" onPress={handleLogin} />
          }
        </View>

        <Pressable
          onPress={() => navigation.navigate('TutorRegister')}
          accessibilityRole="link"
          style={styles.link}
        >
          <Text style={styles.linkText}>¿No tienes cuenta? Regístrate</Text>
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
