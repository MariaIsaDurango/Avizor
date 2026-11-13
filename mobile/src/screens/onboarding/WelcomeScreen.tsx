import { View, Text, StyleSheet, Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import { STORAGE_KEYS } from '../../constants/storage';
import Screen from '../../components/Screen';
import BigText from '../../components/BigText';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'Welcome'>;

async function resetDevStorage(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(STORAGE_KEYS.USER_MODE),
    SecureStore.deleteItemAsync(STORAGE_KEYS.DEVICE_ID),
    SecureStore.deleteItemAsync(STORAGE_KEYS.SENIOR_ID),
    SecureStore.deleteItemAsync('auth_token'),
  ]);
}

export default function WelcomeScreen({ navigation }: Props) {
  function handleDevReset() {
    Alert.alert(
      '[DEV] Borrar datos',
      'Elimina token JWT, device_id y modo de usuario del Keychain.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Borrar',
          style: 'destructive',
          onPress: () =>
            resetDevStorage().then(() =>
              Alert.alert('[DEV]', 'SecureStore limpiado. Reinicia la app.'),
            ),
        },
      ],
    );
  }

  return (
    <Screen style={styles.screen}>
      <View style={styles.hero}>
        <BigText style={styles.logo}>Avizor</BigText>
        <Text style={styles.tagline}>Protección digital para quien quieres</Text>
      </View>
      <Button
        label="Comenzar"
        onPress={() => navigation.navigate('ModeSelection')}
      />
      {__DEV__ && <Button label="[DEV] Borrar datos guardados" onPress={handleDevReset} />}
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    justifyContent: 'space-between',
    paddingBottom: 40,
  },
  hero: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  logo: {
    fontSize: 56,
    color: colors.primary,
  },
  tagline: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.regular,
    color: colors.primary,
    textAlign: 'center',
  },
});
