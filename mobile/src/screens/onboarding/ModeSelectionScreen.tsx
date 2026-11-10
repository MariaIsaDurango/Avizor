import { View, Text, Pressable, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'ModeSelection'>;

export default function ModeSelectionScreen({ navigation }: Props) {
  return (
    <Screen style={styles.screen}>
      <Text style={styles.title}>¿Para quién es esta app?</Text>
      <View style={styles.options}>
        <Pressable
          style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
          onPress={() => navigation.navigate('SeniorConsent')}
          accessibilityRole="button"
          accessibilityLabel="Proteger mi móvil, modo Sénior"
        >
          <MaterialIcons name="shield" size={44} color={colors.primary} />
          <Text style={styles.cardTitle}>Proteger mi móvil</Text>
          <Text style={styles.cardSubtitle}>Quiero que cuiden mi dispositivo</Text>
        </Pressable>

        <Pressable
          style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
          onPress={() => navigation.navigate('TutorLogin')}
          accessibilityRole="button"
          accessibilityLabel="Proteger a mi familiar, modo Tutor"
        >
          <MaterialIcons name="favorite" size={44} color={colors.primary} />
          <Text style={styles.cardTitle}>Proteger a mi familiar</Text>
          <Text style={styles.cardSubtitle}>Quiero cuidar el dispositivo de alguien</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingTop: 40,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 32,
    textAlign: 'center',
  },
  options: {
    gap: 20,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.primary,
    padding: 28,
    alignItems: 'center',
    gap: 10,
  },
  cardPressed: {
    opacity: 0.75,
  },
  cardTitle: {
    fontSize: fontSize.button,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.regular,
    color: colors.primary,
    textAlign: 'center',
  },
});
