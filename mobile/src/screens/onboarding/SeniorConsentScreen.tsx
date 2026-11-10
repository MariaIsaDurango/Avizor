import { View, Text, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as SecureStore from 'expo-secure-store';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { STORAGE_KEYS, CONSENT_TEXT_VERSION } from '../../constants/storage';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorConsent'>;

export default function SeniorConsentScreen({ navigation }: Props) {
  async function handleAccept() {
    await SecureStore.setItemAsync(STORAGE_KEYS.USER_MODE, 'senior');
    await SecureStore.setItemAsync('consent_text_version', CONSENT_TEXT_VERSION);
    navigation.reset({ index: 0, routes: [{ name: 'SeniorPairing' }] });
  }

  return (
    <Screen scrollable>
      <View style={styles.body}>
        <Text style={styles.paragraph}>
          Avizor revisará los SMS y avisos que recibas, y el número de quien te llama, para detectar estafas. Nunca escucha tus llamadas.
        </Text>
        <Text style={styles.paragraph}>
          Antes de revisar un mensaje, borra tu nombre, tus cuentas y otros datos personales.
        </Text>
        <Text style={styles.paragraph}>
          Si un mensaje es peligroso, se guarda sin tus datos durante un máximo de 30 días. Luego se borra.
        </Text>
        <Text style={styles.paragraph}>
          Si detecta algo grave, avisará a tu familiar de confianza. Puedes retirar este permiso cuando quieras.
        </Text>
      </View>
      <Button
        label="Acepto que protejas mi móvil"
        variant="action"
        onPress={handleAccept}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: {
    gap: 20,
    marginBottom: 40,
  },
  paragraph: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.regular,
    color: colors.primary,
    lineHeight: fontSize.body * 1.6,
  },
});
