import { View, Text, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import BigText from '../../components/BigText';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'Welcome'>;

export default function WelcomeScreen({ navigation }: Props) {
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
