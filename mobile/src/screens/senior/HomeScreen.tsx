import { View, Text, StyleSheet } from 'react-native';

export default function SeniorHomeScreen() {
  return (
    <View style={styles.container}>
      <Text>Inicio Sénior</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
