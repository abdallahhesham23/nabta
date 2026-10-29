import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { theme } from '@/lib/theme';

export function Screen({ children }: { children: ReactNode }) {
  return <ScrollView style={s.screen} contentContainerStyle={s.content}>{children}</ScrollView>;
}

export function Card({ children, onPress }: { children: ReactNode; onPress?: () => void }) {
  if (!onPress) return <View style={s.card}>{children}</View>;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.card, pressed && { opacity: 0.7 }]} accessibilityRole="button">
      {children}
    </Pressable>
  );
}

export const Title = ({ children }: { children: ReactNode }) => <Text style={s.title}>{children}</Text>;
export const H2 = ({ children }: { children: ReactNode }) => <Text style={s.h2}>{children}</Text>;
export const Body = ({ children, muted }: { children: ReactNode; muted?: boolean }) =>
  <Text style={[s.body, muted && { color: theme.muted }]}>{children}</Text>;

export function Badge({ label, color }: { label: string; color: string }) {
  return <View style={[s.badge, { backgroundColor: color }]}><Text style={s.badgeText}>{label}</Text></View>;
}

export function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <View style={s.stat}>
      <Text style={s.statLabel}>{label}</Text>
      <Text style={s.statValue}>{value}</Text>
      {note ? <Text style={s.statNote}>{note}</Text> : null}
    </View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={[s.chip, selected && s.chipOn]} accessibilityRole="button"
      accessibilityState={{ selected }}>
      <Text style={[s.chipText, selected && { color: '#fff' }]}>{label}</Text>
    </Pressable>
  );
}

export const Chips = ({ children }: { children: ReactNode }) => <View style={s.chips}>{children}</View>;

export function Button({ label, onPress, busy, secondary }: { label: string; onPress: () => void; busy?: boolean; secondary?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={busy} accessibilityRole="button"
      style={({ pressed }) => [s.button, secondary && s.buttonSecondary, (pressed || busy) && { opacity: 0.7 }]}>
      {busy ? <ActivityIndicator color={secondary ? theme.primary : '#fff'} />
        : <Text style={[s.buttonText, secondary && { color: theme.primary }]}>{label}</Text>}
    </Pressable>
  );
}

export function Field({ label, ...props }: { label: string } & TextInputProps) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={s.statLabel}>{label}</Text>
      <TextInput placeholderTextColor={theme.muted} style={s.input} {...props} />
    </View>
  );
}

export function Loading({ error }: { error?: string }) {
  return (
    <View style={s.center}>
      {error ? <Body>تعذّر تحميل البيانات. تأكد من الاتصال بالإنترنت وحاول تاني.{'\n'}{error}</Body>
        : <ActivityIndicator size="large" color={theme.primary} />}
    </View>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.bg },
  content: { padding: 16, gap: 12, paddingBottom: 40 },
  card: { backgroundColor: theme.card, borderRadius: theme.radius, padding: 16, gap: 8, borderWidth: 1, borderColor: theme.border },
  title: { fontSize: 26, fontWeight: '800', color: theme.text },
  h2: { fontSize: 20, fontWeight: '700', color: theme.text },
  body: { fontSize: 17, lineHeight: 26, color: theme.text },
  badge: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 12, paddingVertical: 4 },
  badgeText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  stat: { flexGrow: 1, flexBasis: '45%', backgroundColor: theme.card, borderRadius: theme.radius, padding: 14, gap: 4, borderWidth: 1, borderColor: theme.border },
  statLabel: { fontSize: 15, color: theme.muted },
  statValue: { fontSize: 24, fontWeight: '800', color: theme.text },
  statNote: { fontSize: 13, color: theme.muted },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderRadius: 999, borderWidth: 1, borderColor: theme.primary, paddingHorizontal: 14, paddingVertical: 8, minHeight: 40, justifyContent: 'center' },
  chipOn: { backgroundColor: theme.primary },
  chipText: { fontSize: 16, color: theme.primary, fontWeight: '600' },
  button: { backgroundColor: theme.primary, borderRadius: theme.radius, paddingVertical: 14, alignItems: 'center', minHeight: 52, justifyContent: 'center' },
  buttonSecondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: theme.primary },
  buttonText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  input: { borderWidth: 1, borderColor: theme.border, borderRadius: 10, backgroundColor: '#fff', paddingHorizontal: 12, paddingVertical: 12, fontSize: 18, color: theme.text },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: theme.bg },
});
