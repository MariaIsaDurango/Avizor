import { View, Text, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as SecureStore from 'expo-secure-store';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { STORAGE_KEYS } from '../../constants/storage';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorConsent'>;

export default function SeniorConsentScreen({ navigation }: Props) {
  async function handleAccept() {
    await SecureStore.setItemAsync(STORAGE_KEYS.USER_MODE, 'senior');
    navigation.reset({ index: 0, routes: [{ name: 'SeniorHome' }] });
  }

  return (
    <Screen scrollable>
      <View style={styles.body}>
        <Text style={styles.paragraph}>
          Avizor revisará los mensajes y llamadas que recibas para detectar posibles estafas.
        </Text>
        <Text style={styles.paragraph}>
          Nunca leerá el contenido de tus conversaciones personales ni guardará información tuya.
        </Text>
        <Text style={styles.paragraph}>
          Si detecta algo sospechoso, avisará a tu familiar de confianza.
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
