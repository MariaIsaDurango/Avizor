import { View, Text, StyleSheet } from 'react-native';

export default function TutorRegisterScreen() {
  return (
    <View style={styles.container}>
      <Text>Registro Tutor</Text>
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
