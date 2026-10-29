import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Body, Card, Chip, Chips, Loading, Screen } from '@/components/ui';
import { useMarket, type Cell } from '@/lib/data';
import { big, egp, num, OUTLOOK, pct } from '@/lib/format';
import { theme } from '@/lib/theme';

const MAX = 3;
const ROWS: { label: string; value: (c: Cell) => string }[] = [
  { label: 'حالة السوق', value: (c) => (c.outlook ? OUTLOOK[c.outlook].label : '—') },
  { label: 'المعروض مقابل المعتاد', value: (c) => pct(c.gap_pct) },
  { label: 'سعر المزرعة المتوقع (كجم)', value: (c) => egp(c.price_egp_per_kg) },
  { label: 'إنتاجية الفدان (طن)', value: (c) => num(c.yield_t_per_feddan, 1) },
  { label: 'إيراد الفدان المتوقع', value: (c) => egp(c.revenue_egp_per_feddan) },
  { label: 'المساحة على مستوى مصر (فدان)', value: (c) => big(c.area_now_feddan) },
];

export default function CompareScreen() {
  const { data, error } = useMarket();
  const [picked, setPicked] = useState<string[]>(['tomato', 'potato', 'onion']);
  if (!data) return <Loading error={error} />;

  const toggle = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < MAX ? [...p, id] : [...p.slice(1), id]));
  const cols = picked.filter((id) => data.cells[id]);
  const name = (id: string) => data.crops.find((c) => c.id === id)?.name_ar ?? id;

  return (
    <Screen>
      <Body muted>اختار لحد ٣ محاصيل وقارن بينهم على نفس الأرقام.</Body>
      <Chips>
        {data.crops.map((c) => <Chip key={c.id} label={c.name_ar} selected={picked.includes(c.id)} onPress={() => toggle(c.id)} />)}
      </Chips>
      <Card>
        <View style={st.row}>
          <Text style={[st.label, st.head]}> </Text>
          {cols.map((id) => <Text key={id} style={[st.cell, st.head]}>{name(id)}</Text>)}
        </View>
        {ROWS.map((r) => (
          <View key={r.label} style={st.row}>
            <Text style={st.label}>{r.label}</Text>
            {cols.map((id) => <Text key={id} style={st.cell}>{r.value(data.cells[id])}</Text>)}
          </View>
        ))}
      </Card>
      <Body muted>الإيراد قبل خصم تكاليف الزراعة. الأسعار المتوقعة تقديرية.</Body>
    </Screen>
  );
}

const st = StyleSheet.create({
  row: { flexDirection: 'row', borderBottomWidth: 1, borderColor: theme.border, paddingVertical: 10, gap: 6 },
  label: { flex: 1.4, fontSize: 15, color: theme.muted },
  cell: { flex: 1, fontSize: 16, color: theme.text, fontWeight: '600', textAlign: 'center' },
  head: { fontSize: 17, fontWeight: '800', color: theme.text },
});
