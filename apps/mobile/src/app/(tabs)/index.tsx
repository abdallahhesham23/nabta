import { router } from 'expo-router';
import { View } from 'react-native';

import { Badge, Body, Card, H2, Loading, Screen } from '@/components/ui';
import { nextSeason, useMarket } from '@/lib/data';
import { egp, OUTLOOK, SEASON, yr } from '@/lib/format';

const ORDER = { vegetable: 0, field: 1, fruit: 2 };

export default function MarketScreen() {
  const { data, error, stale } = useMarket();
  if (!data) return <Loading error={error} />;
  const { season, year } = nextSeason();
  const crops = [...data.crops].sort((a, b) => ORDER[a.category] - ORDER[b.category] || a.name_ar.localeCompare(b.name_ar, 'ar'));

  return (
    <Screen>
      {stale ? <Body muted>بنعرض آخر بيانات محفوظة على الموبايل لحد ما التحديث يوصل.</Body> : null}
      <Body muted>الموسم القادم: {SEASON[season]} {yr(year)}. اختار محصول عشان تشوف المساحة والإنتاج والعرض والطلب قبل ما تزرع.</Body>
      {crops.map((c) => {
        const cell = data.cells[c.id];
        const obour = data.obour[c.id];
        const look = cell?.outlook ? OUTLOOK[cell.outlook] : null;
        return (
          <Card key={c.id} onPress={() => router.push(`/crop/${c.id}`)}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <H2>{c.name_ar}</H2>
              {look ? <Badge label={look.label} color={look.color} /> : null}
            </View>
            <Body muted>
              السعر المتوقع للمزارع عند الحصاد: {egp(cell?.price_egp_per_kg)} للكيلو
              {obour ? `\nسوق العبور النهارده: ${egp(obour.min_egp_per_kg)} – ${egp(obour.max_egp_per_kg)}` : ''}
            </Body>
          </Card>
        );
      })}
    </Screen>
  );
}
