import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Badge, Body, Card, H2, Loading, Screen, Stat } from '@/components/ui';
import { fetchForecast, useMarket, type Forecast } from '@/lib/data';
import { big, dayMonth, egp, monthName, num, OUTLOOK, pct, yr } from '@/lib/format';
import { theme } from '@/lib/theme';

export default function CropScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, error } = useMarket();
  const [forecast, setForecast] = useState<Forecast[]>([]);
  useEffect(() => { fetchForecast(id).then(setForecast, () => setForecast([])); }, [id]);

  if (!data) return <Loading error={error} />;
  const crop = data.crops.find((c) => c.id === id);
  const cell = data.cells[id];
  if (!crop || !cell) return <Loading error="المحصول غير موجود" />;
  const look = cell.outlook ? OUTLOOK[cell.outlook] : null;
  const obour = data.obour[id];
  // Share of demand covered by imports (demand = production + imports, 3-year average).
  const importShare = cell.demand_t ? (cell.demand_t - cell.last_year_prod_t) / cell.demand_t : 0;

  return (
    <Screen>
      <Stack.Screen options={{ title: crop.name_ar }} />
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <H2>العرض والطلب</H2>
          {look ? <Badge label={look.label} color={look.color} /> : null}
        </View>
        <Body>{look ? look.hint : 'مفيش بيانات تجارة كفاية لتقدير العرض والطلب.'}</Body>
        {cell.gap_pct != null ? <Body muted>المعروض المتوقع مقارنة بالمعتاد: {pct(cell.gap_pct)}</Body> : null}
        {importShare > 0.2 ? (
          <Body muted>مصر بتستورد حوالي {num(importShare * 100, 0)}٪ من احتياجها من المحصول ده، يعني فيه مجال لزيادة الإنتاج المحلي.</Body>
        ) : null}
      </Card>

      <View style={st.grid}>
        <Stat label="المساحة المزروعة" value={`${big(cell.area_now_feddan)} فدان`} note={`على مستوى الجمهورية (${yr(cell.data_year)})`} />
        <Stat label="الإنتاج المتوقع" value={`${big(cell.expected_prod_t)} طن`} note="بمتوسط إنتاجية آخر ٣ سنين" />
        <Stat label="إنتاج العام السابق" value={`${big(cell.last_year_prod_t)} طن`} note={`سنة ${yr(cell.data_year)}`} />
        <Stat label="اللي السوق بيستوعبه عادة" value={`${big(cell.demand_t)} طن`} note="استهلاك وتصدير، متوسط ٣ سنين" />
      </View>

      <Card>
        <H2>مزارعين نبتة الموسم ده</H2>
        <Body>
          {cell.intending_farms
            ? `${num(cell.intending_farms, 0)} مزارع ناويين يزرعوا ${big(cell.intended_area_feddan)} فدان من المحصول ده.`
            : 'لسه عدد المزارعين اللي سجّلوا نيتهم قليل. بنعرض الرقم لما يوصلوا ١٠ مزارعين أو أكتر عشان نحافظ على خصوصية كل واحد.'}
        </Body>
      </Card>

      <Card>
        <H2>الأسعار</H2>
        <Body>السعر المتوقع للمزارع عند الحصاد: {egp(cell.price_egp_per_kg)} للكيلو</Body>
        {obour ? <Body>سوق العبور ({dayMonth(obour.price_date)}): من {egp(obour.min_egp_per_kg)} لـ {egp(obour.max_egp_per_kg)} للكيلو</Body> : null}
        <Body>متوسط إنتاجية الفدان: {num(cell.yield_t_per_feddan, 1)} طن</Body>
        <Body>الإيراد المتوقع للفدان (قبل التكاليف): {egp(cell.revenue_egp_per_feddan)}</Body>
      </Card>

      {forecast.length ? (
        <Card>
          <H2>توقع سعر المزرعة لكل شهر</H2>
          <ForecastBars rows={forecast} />
          <Body muted>تقدير تقريبي من أسعار السنين اللي فاتت، ومدى الخطأ ممكن يوصل لـ ٣٠٪ في الاتجاهين.</Body>
        </Card>
      ) : null}

      <Body muted>المصادر: منظمة الأغذية والزراعة (FAOSTAT) لبيانات المساحة والإنتاج والتجارة حتى {yr(cell.data_year)}، وأسعار سوق العبور اليومية.</Body>
    </Screen>
  );
}

function ForecastBars({ rows }: { rows: Forecast[] }) {
  const max = Math.max(...rows.map((r) => r.price_egp_per_kg));
  return (
    <View style={st.bars} accessibilityLabel="رسم بياني لتوقع الأسعار">
      {rows.map((r, i) => (
        <View key={r.target_month} style={st.barCol}>
          <Text style={st.barValue}>{num(r.price_egp_per_kg, 0)}</Text>
          <View style={[st.bar, { height: 8 + (r.price_egp_per_kg / max) * 110 }]} />
          {/* every third month: twelve labels don't fit on a phone */}
          <Text style={st.barLabel} numberOfLines={1}>{i % 3 === 0 ? monthName(r.target_month) : ' '}</Text>
        </View>
      ))}
    </View>
  );
}

const st = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, height: 160 },
  barCol: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', gap: 4 },
  bar: { width: '80%', backgroundColor: theme.primary, borderRadius: 4 },
  barValue: { fontSize: 11, color: theme.muted },
  barLabel: { fontSize: 11, color: theme.muted, width: 60, textAlign: 'center' },
});
