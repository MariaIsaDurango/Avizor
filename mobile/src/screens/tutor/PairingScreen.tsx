import { View, Text, StyleSheet } from 'react-native';

export default function TutorPairingScreen() {
  return (
    <View style={styles.container}>
      <Text>Vinculación con dispositivo Sénior</Text>
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
