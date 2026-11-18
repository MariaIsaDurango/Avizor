import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { verifyEmail, resendVerification } from '../../services/auth';

type Props = NativeStackScreenProps<RootStackParamList, 'VerifyEmail'>;

export default function VerifyEmailScreen({ navigation, route }: Props) {
  const { email } = route.params;
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendMsg, setResendMsg] = useState<string | null>(null);

  async function handleVerify() {
    if (code.length !== 6) {
      setError('Introduce los 6 dígitos del código.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await verifyEmail(email, code);
      // Verificado — el usuario ya puede hacer login; lo hacemos internamente
      // navegando al login para que introduzca su contraseña (el token no está disponible aquí)
      navigation.reset({ index: 0, routes: [{ name: 'TutorLogin', params: { email } }] });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Código incorrecto. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResending(true);
    setResendMsg(null);
    setError(null);
    try {
      await resendVerification(email);
      setResendMsg('Código reenviado. Revisa tu correo.');
    } catch {
      setError('No se pudo reenviar el código. Inténtalo más tarde.');
    } finally {
      setResending(false);
    }
  }

  return (
    <Screen scrollable>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <Pressable onPress={() => navigation.goBack()} style={styles.back}>
          <Text style={styles.backText}>‹ Volver</Text>
        </Pressable>

        <Text style={styles.title}>Verifica tu email</Text>
        <Text style={styles.subtitle}>
          Te enviamos un código de 6 dígitos a{'\n'}
          <Text style={styles.email}>{email}</Text>
        </Text>

        <TextInput
          style={styles.codeInput}
          placeholder="000000"
          placeholderTextColor={`${colors.primary}55`}
          value={code}
          onChangeText={(v) => { setCode(v.replace(/\D/g, '').slice(0, 6)); setError(null); }}
          keyboardType="number-pad"
          maxLength={6}
          textAlign="center"
          autoFocus
        />

        {error && <Text style={styles.error}>{error}</Text>}
        {resendMsg && <Text style={styles.success}>{resendMsg}</Text>}

        <View style={styles.buttonWrapper}>
          {loading
            ? <ActivityIndicator color={colors.primary} size="large" />
            : <Button label="Verificar cuenta" onPress={handleVerify} />
          }
        </View>

        <View style={styles.resendRow}>
          <Text style={styles.resendLabel}>¿No recibiste el código?</Text>
          {resending
            ? <ActivityIndicator color={colors.primary} size="small" />
            : (
              <Pressable onPress={handleResend} accessibilityRole="button">
                <Text style={styles.resendLink}>Reenviar código</Text>
              </Pressable>
            )
          }
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  back: { marginBottom: 24 },
  backText: { fontSize: fontSize.body, color: colors.primary },

  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 22,
    opacity: 0.75,
  },
  email: {
    fontWeight: fontWeight.bold,
    opacity: 1,
  },

  codeInput: {
    borderWidth: 2,
    borderColor: colors.primary,
    borderRadius: 12,
    padding: 18,
    fontSize: 32,
    letterSpacing: 12,
    color: colors.primary,
    backgroundColor: colors.white,
    marginBottom: 16,
    fontWeight: fontWeight.bold,
  },

  error: {
    color: colors.alert,
    fontSize: fontSize.body,
    marginBottom: 12,
    textAlign: 'center',
  },
  success: {
    color: colors.success,
    fontSize: fontSize.body,
    marginBottom: 12,
    textAlign: 'center',
  },

  buttonWrapper: { marginTop: 8, marginBottom: 24 },

  resendRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 6,
  },
  resendLabel: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.6,
  },
  resendLink: {
    fontSize: fontSize.body,
    color: colors.primary,
    fontWeight: fontWeight.bold,
    textDecorationLine: 'underline',
  },
});
