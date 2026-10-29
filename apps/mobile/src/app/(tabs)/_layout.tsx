import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { theme } from '@/lib/theme';

const icon = (glyph: string) => function TabIcon() {
  return <Text style={{ fontSize: 22 }}>{glyph}</Text>;
};

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{
      headerStyle: { backgroundColor: theme.primary }, headerTintColor: '#fff',
      headerTitleStyle: { fontWeight: '700' }, tabBarActiveTintColor: theme.primary,
      tabBarLabelStyle: { fontSize: 14, fontWeight: '600' }, tabBarStyle: { height: 64, paddingBottom: 8 },
    }}>
      <Tabs.Screen name="index" options={{ title: 'السوق', headerTitle: 'نبتة · السوق', tabBarIcon: icon('📊') }} />
      <Tabs.Screen name="compare" options={{ title: 'قارن', headerTitle: 'قارن بين المحاصيل', tabBarIcon: icon('⚖️') }} />
      <Tabs.Screen name="farm" options={{ title: 'مزرعتي', headerTitle: 'مزرعتي', tabBarIcon: icon('🌱') }} />
    </Tabs>
  );
}
