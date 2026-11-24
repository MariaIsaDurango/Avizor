import { useState } from 'react';
import { View, Text, Image, TextInput, Pressable, ActivityIndicator, KeyboardAvoidingView, Platform } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import { authStyles as a } from '../../styles/auth';
import { verifyEmail, resendVerification } from '../../services/auth';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'VerifyEmail'>;

export default function VerifyEmailScreen({ navigation, route }: Props) {
  const { email }                          = route.params;
  const [code, setCode]                   = useState('');
  const [loading, setLoading]             = useState(false);
  const [resending, setResending]         = useState(false);
  const [error, setError]                 = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState(false);

  async function handleVerify() {
    if (code.length !== 6) { setError('Introduce los 6 dígitos del código.'); return; }
    setLoading(true);
    setError(null);
    try {
      await verifyEmail(email, code);
      navigation.reset({ index: 0, routes: [{ name: 'TutorLogin', params: { email } }] });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Código incorrecto. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResending(true);
    setError(null);
    setResendSuccess(false);
    try {
      await resendVerification(email);
      setResendSuccess(true);
    } catch {
      setError('No se pudo reenviar el código. Inténtalo más tarde.');
    } finally {
      setResending(false);
    }
  }

  return (
    <Screen scrollable>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>

        <Pressable onPress={() => navigation.goBack()} style={a.back} accessibilityRole="button" accessibilityLabel="Volver">
          <Text style={a.backText}>‹ Volver</Text>
        </Pressable>

        <View style={a.brand}>
          <Image source={require('../../../assets/logo-web.png')} style={a.logo} resizeMode="contain" accessibilityLabel="" />
          <Text style={a.brandName}>Avizor</Text>
        </View>

        <Text style={a.heading}>Verifica tu email</Text>
        <Text style={a.subtitle}>
          Hemos enviado un código de 6 dígitos a{'\n'}
          <Text style={a.subtitleBold}>{email}</Text>
        </Text>

        {error && (
          <View style={a.alertError}>
            <Text style={a.alertErrorText}>{error}</Text>
          </View>
        )}

        {resendSuccess && (
          <View style={a.alertSuccess}>
            <Text style={a.alertSuccessText}>Código reenviado. Revisa tu bandeja de entrada.</Text>
          </View>
        )}

        <View style={a.formGroup}>
          <Text style={a.label}>Código de verificación</Text>
          <TextInput
            style={[a.input, { fontSize: 28, letterSpacing: 10, textAlign: 'center', fontWeight: '700', paddingVertical: 16 }]}
            placeholder="000000"
            placeholderTextColor="#ccc"
            value={code}
            onChangeText={(v) => { setCode(v.replace(/\D/g, '').slice(0, 6)); setError(null); }}
            keyboardType="number-pad"
            maxLength={6}
            autoFocus
          />
        </View>

        {loading
          ? <ActivityIndicator color="#164E55" size="large" style={{ marginVertical: 8 }} />
          : (
            <Pressable
              style={({ pressed }) => [a.submitBtn, pressed && a.submitBtnDisabled]}
              onPress={handleVerify}
              accessibilityRole="button"
              accessibilityLabel="Verificar cuenta"
            >
              <Text style={a.submitText}>Verificar</Text>
            </Pressable>
          )
        }

        <View style={[a.footerLink, { flexDirection: 'row', gap: 4 }]}>
          <Text style={a.footerText}>¿No recibiste el código?</Text>
          {resending
            ? <ActivityIndicator color="#164E55" size="small" />
            : (
              <Pressable onPress={handleResend} accessibilityRole="button">
                <Text style={a.footerTextBold}>Reenviar</Text>
              </Pressable>
            )
          }
        </View>

      </KeyboardAvoidingView>
    </Screen>
  );
}
