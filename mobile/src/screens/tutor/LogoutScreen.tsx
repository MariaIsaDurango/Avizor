import { View, Text, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { logout } from '../../services/auth';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorLogout'>;

export default function LogoutScreen({ navigation }: Props) {
  async function handleLogout() {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: 'TutorLogin' }] });
  }

  return (
    <Screen style={styles.screen}>
      <View style={styles.content}>
        <Text style={styles.title}>¿Cerrar sesión?</Text>
        <Text style={styles.subtitle}>
          Se eliminará tu sesión de este dispositivo.
        </Text>
      </View>
      <View style={styles.buttons}>
        <Button label="Cerrar sesión" variant="alert" onPress={handleLogout} />
        <Button label="Cancelar" onPress={() => navigation.goBack()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    justifyContent: 'space-between',
    paddingBottom: 40,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    gap: 16,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: fontSize.body,
    color: colors.primary,
    textAlign: 'center',
  },
  buttons: {
    gap: 12,
  },
});
