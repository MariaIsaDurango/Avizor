import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  TouchableWithoutFeedback,
  Keyboard,
  Platform,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import BigText from '../../components/BigText';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { redeemPairing } from '../../services/pairing';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorPairing'>;

export default function SeniorPairingScreen({ navigation }: Props) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRedeem() {
    if (code.length !== 6) {
      setError('El código tiene 6 dígitos.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await redeemPairing(code);
      navigation.reset({ index: 0, routes: [{ name: 'SeniorHome' }] });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al vincular el dispositivo.');
    } finally {
      setLoading(false);
    }
  }

  // TEMP: solo desarrollo — eliminar antes de producción
  function handleDevReset() {
    Alert.alert('[DEV] Borrar datos', 'Elimina token, device_id y modo de usuario.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Borrar',
        style: 'destructive',
        onPress: () =>
          Promise.all([
            SecureStore.deleteItemAsync('user_mode'),
            SecureStore.deleteItemAsync('device_id'),
            SecureStore.deleteItemAsync('auth_token'),
          ]).then(() => navigation.reset({ index: 0, routes: [{ name: 'Welcome' }] })),
      },
    ]);
  }

  return (
    <Screen style={styles.screen}>
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={20}
      >
        <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
          <View style={styles.inner}>
            <View style={styles.top}>
              <BigText style={styles.title}>Vincula tu móvil</BigText>
              <Text style={styles.instructions}>
                Pide a tu familiar el código de 6 dígitos que aparece en su pantalla e introdúcelo aquí.
              </Text>
              <TextInput
                style={styles.input}
                value={code}
                onChangeText={(v) => { setCode(v.replace(/\D/g, '')); setError(null); }}
                keyboardType="number-pad"
                maxLength={6}
                placeholder="– – – – – –"
                placeholderTextColor={colors.primary + '55'}
                autoFocus
                accessibilityLabel="Código de vinculación de 6 dígitos"
              />
              {error !== null && <Text style={styles.error}>{error}</Text>}
            </View>

            <View style={styles.footer}>
              {loading
                ? <ActivityIndicator size="large" color={colors.primary} />
                : (
                  <Button
                    label="Vincular"
                    variant="action"
                    disabled={code.length !== 6}
                    onPress={handleRedeem}
                  />
                )
              }
              {/* TEMP: solo desarrollo — eliminar antes de producción */}
              <Button label="[DEV] Borrar datos guardados" onPress={handleDevReset} />
            </View>
          </View>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingBottom: 0,
  },
  keyboardView: {
    flex: 1,
  },
  inner: {
    flex: 1,
    justifyContent: 'space-between',
    paddingBottom: 40,
  },
  top: {
    alignItems: 'center',
    marginTop: 32,
    gap: 24,
  },
  title: {
    color: colors.primary,
    textAlign: 'center',
  },
  instructions: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
    lineHeight: fontSize.body * 1.6,
    opacity: 0.8,
  },
  input: {
    borderWidth: 2,
    borderColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 24,
    fontSize: 36,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    backgroundColor: colors.white,
    textAlign: 'center',
    letterSpacing: 12,
    width: '70%',
  },
  error: {
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
  },
  footer: {
    gap: 12,
  },
});
