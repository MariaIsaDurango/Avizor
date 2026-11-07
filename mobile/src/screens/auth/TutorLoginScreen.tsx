import { View, Text, StyleSheet } from 'react-native';

export default function TutorLoginScreen() {
  return (
    <View style={styles.container}>
      <Text>Inicio de sesión Tutor</Text>
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
