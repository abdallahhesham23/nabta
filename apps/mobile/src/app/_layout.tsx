import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { theme } from '@/lib/theme';

// Native RTL comes from the expo-localization plugin (forcesRTL); the web build needs dir="rtl".
const webRtl = Platform.OS === 'web' ? ({ dir: 'rtl', lang: 'ar' } as object) : {};

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <View style={{ flex: 1 }} {...webRtl}>
        <Stack screenOptions={{
          headerStyle: { backgroundColor: theme.primary }, headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: '700' }, contentStyle: { backgroundColor: theme.bg },
        }}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="crop/[id]" options={{ title: 'تقرير المحصول' }} />
        </Stack>
      </View>
    </SafeAreaProvider>
  );
}
