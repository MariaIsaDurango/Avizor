import { View, Text, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorDashboard'>;

export default function TutorDashboardScreen({ navigation }: Props) {
  return (
    <Screen style={styles.screen}>
      <Text style={styles.title}>Panel de control</Text>
      <View style={styles.footer}>
        <Button
          label="Vincular dispositivo Sénior"
          onPress={() => navigation.navigate('TutorPairing')}
        />
        <Button
          label="Cerrar sesión"
          variant="alert"
          onPress={() => navigation.navigate('TutorLogout')}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    justifyContent: 'space-between',
    paddingBottom: 40,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginTop: 24,
    textAlign: 'center',
  },
  footer: {
    gap: 12,
  },
});
