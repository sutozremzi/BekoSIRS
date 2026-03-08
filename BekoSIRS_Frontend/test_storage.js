import AsyncStorage from '@react-native-async-storage/async-storage';

async function testStorage() {
  await AsyncStorage.removeItem('userRole');
  await AsyncStorage.removeItem('user_role');
  console.log("Deleted");
}
testStorage();
