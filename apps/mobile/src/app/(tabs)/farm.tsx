import type { Session } from '@supabase/supabase-js';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';

import { Body, Button, Card, Chip, Chips, Field, H2, Loading, Screen } from '@/components/ui';
import { nextSeason, useMarket, type Market, type Season } from '@/lib/data';
import { egp, num, parseNum, SEASON, SOIL, WATER, yr } from '@/lib/format';
import { supabase } from '@/lib/supabase';

export default function FarmScreen() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => data.subscription.unsubscribe();
  }, []);
  const market = useMarket();

  if (session === undefined || !market.data) return <Loading error={market.error} />;
  return session ? <Farm userId={session.user.id} market={market.data} /> : <Login />;
}

// ---------------------------------------------------------------- login (WhatsApp one-time code)

function Login() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const intl = '+2' + phone.replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/\D/g, '');

  async function send() {
    if (!/^\+201[0125]\d{8}$/.test(intl)) return setMsg('اكتب رقم موبايل مصري صحيح، مثلاً ٠١٠١٢٣٤٥٦٧٨');
    setBusy(true); setMsg('');
    const { error } = await supabase.auth.signInWithOtp({ phone: intl, options: { channel: 'whatsapp' } });
    setBusy(false);
    if (error) return setMsg('تعذّر إرسال الكود دلوقتي. تسجيل الدخول بواتساب لسه بيتجهّز، جرّب بعدين.');
    setSent(true); setMsg('بعتنالك كود على واتساب.');
  }

  async function verify() {
    setBusy(true); setMsg('');
    const { error } = await supabase.auth.verifyOtp({ phone: intl, token: code.trim(), type: 'sms' });
    setBusy(false);
    if (error) setMsg('الكود مش صحيح أو انتهى. اطلب كود جديد.');
  }

  return (
    <Screen>
      <Card>
        <H2>سجّل دخولك</H2>
        <Body muted>سجّل برقم موبايلك عشان تحفظ بيانات أرضك وتشوف التوصيات الخاصة بيك.</Body>
        <Field label="رقم الموبايل" value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="٠١٠١٢٣٤٥٦٧٨" />
        {sent ? <Field label="الكود" value={code} onChangeText={setCode} keyboardType="number-pad" /> : null}
        {msg ? <Body>{msg}</Body> : null}
        <Button label={sent ? 'تأكيد الكود' : 'ابعت الكود على واتساب'} onPress={sent ? verify : send} busy={busy} />
      </Card>
    </Screen>
  );
}

// ---------------------------------------------------------------- the farmer's own data

type Farmer = { full_name: string | null; gov_id: string | null; capital_egp: number | null };
type Plot = { id: number; area_feddan: number; soil: string | null; water_source: string | null };
type Intention = { id: number; crop_id: string; season: Season; year: number; area_feddan: number; status: string; harvest: { yield_t: number } | null };
type Report = { yield_t: number };
type Rec = { crop_id: string; rank: number; evi: number; expected_profit_egp_per_feddan: number; expected_price_egp_per_kg: number; cost_egp_per_feddan: number };

function Farm({ userId, market }: { userId: string; market: Market }) {
  const [farmer, setFarmer] = useState<Farmer | null>(null);
  const [plot, setPlot] = useState<Plot | null>(null);
  const [intentions, setIntentions] = useState<Intention[]>([]);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [loaded, setLoaded] = useState(false);

  const reload = useCallback(async () => {
    const [f, p, i, r] = await Promise.all([
      supabase.from('farmers').select('full_name, gov_id, capital_egp').eq('id', userId).maybeSingle(),
      supabase.from('plots').select('id, area_feddan, soil, water_source').order('id').limit(1).maybeSingle(),
      supabase.from('intentions').select('id, crop_id, season, year, area_feddan, status, harvest_reports(yield_t)').order('id', { ascending: false }),
      supabase.from('recommendations').select('crop_id, rank, evi, expected_profit_egp_per_feddan, expected_price_egp_per_kg, cost_egp_per_feddan').order('rank'),
    ]);
    // harvest_reports.intention_id is unique, so the API may embed one object instead of a list
    const intents = (i.data ?? []).map(({ harvest_reports: h, ...rest }) => ({
      ...rest, harvest: (Array.isArray(h) ? h[0] : h) as Report | null ?? null,
    })) as Intention[];
    setFarmer(f.data); setPlot(p.data); setIntentions(intents); setRecs((r.data ?? []) as Rec[]);
    setLoaded(true);
  }, [userId]);
  useEffect(() => { reload(); }, [reload]);

  if (!loaded) return <Loading />;
  const cropName = (id: string) => market.crops.find((c) => c.id === id)?.name_ar ?? id;

  return (
    <Screen>
      <ProfileForm userId={userId} farmer={farmer} market={market} onSaved={reload} />
      {farmer ? <PlotForm plot={plot} onSaved={reload} /> : null}
      {plot ? <Recommendations recs={recs} cropName={cropName} /> : null}
      {plot ? <Plans plot={plot} intentions={intentions} market={market} cropName={cropName} onSaved={reload} /> : null}
      <Button label="تسجيل الخروج" secondary onPress={() => supabase.auth.signOut()} />
    </Screen>
  );
}

function ProfileForm({ userId, farmer, market, onSaved }: { userId: string; farmer: Farmer | null; market: Market; onSaved: () => void }) {
  const [name, setName] = useState(farmer?.full_name ?? '');
  const [gov, setGov] = useState(farmer?.gov_id ?? null);
  const [capital, setCapital] = useState(farmer?.capital_egp != null ? String(farmer.capital_egp) : '');
  const [msg, setMsg] = useState('');

  async function save() {
    const cap = capital ? parseNum(capital) : null;
    if (capital && cap == null) return setMsg('اكتب رأس المال بالأرقام بس.');
    const { error } = await supabase.from('farmers').upsert({ id: userId, full_name: name || null, gov_id: gov, capital_egp: cap });
    setMsg(error ? 'حصلت مشكلة في الحفظ، حاول تاني.' : 'اتحفظ.');
    if (!error) onSaved();
  }

  return (
    <Card>
      <H2>بياناتي</H2>
      <Field label="الاسم" value={name} onChangeText={setName} />
      <Body muted>المحافظة</Body>
      <Chips>{market.governorates.map((g) => <Chip key={g.id} label={g.name_ar} selected={gov === g.id} onPress={() => setGov(g.id)} />)}</Chips>
      <Field label="رأس المال المتاح للزراعة (جنيه)" value={capital} onChangeText={setCapital} keyboardType="numeric" />
      {msg ? <Body>{msg}</Body> : null}
      <Button label="حفظ" onPress={save} />
    </Card>
  );
}

function PlotForm({ plot, onSaved }: { plot: Plot | null; onSaved: () => void }) {
  const [area, setArea] = useState(plot ? String(plot.area_feddan) : '');
  const [soil, setSoil] = useState(plot?.soil ?? null);
  const [water, setWater] = useState(plot?.water_source ?? null);
  const [msg, setMsg] = useState('');

  async function save() {
    const a = parseNum(area);
    if (!a || a <= 0) return setMsg('اكتب مساحة الأرض بالفدان، مثلاً ٢ أو ٠٫٥');
    const row = { area_feddan: a, soil, water_source: water };
    const { error } = plot ? await supabase.from('plots').update(row).eq('id', plot.id) : await supabase.from('plots').insert(row);
    setMsg(error ? 'حصلت مشكلة في الحفظ، حاول تاني.' : 'اتحفظ.');
    if (!error) onSaved();
  }

  return (
    <Card>
      <H2>أرضي</H2>
      <Field label="المساحة (فدان)" value={area} onChangeText={setArea} keyboardType="numeric" />
      <Body muted>نوع التربة</Body>
      <Chips>{Object.entries(SOIL).map(([k, v]) => <Chip key={k} label={v} selected={soil === k} onPress={() => setSoil(k)} />)}</Chips>
      <Body muted>مصدر المية</Body>
      <Chips>{Object.entries(WATER).map(([k, v]) => <Chip key={k} label={v} selected={water === k} onPress={() => setWater(k)} />)}</Chips>
      {msg ? <Body>{msg}</Body> : null}
      <Button label="حفظ" onPress={save} />
    </Card>
  );
}

function Recommendations({ recs, cropName }: { recs: Rec[]; cropName: (id: string) => string }) {
  return (
    <Card>
      <H2>التوصيات ليك</H2>
      {recs.length === 0 ? (
        <Body muted>التوصيات بتظهر هنا لما تكتمل بيانات تكاليف الزراعة لكل محصول. بنحدّث الحسابات كل يوم.</Body>
      ) : recs.map((r) => (
        <View key={r.crop_id} style={{ gap: 2, paddingVertical: 6 }}>
          <Body>{num(r.rank, 0)}. {cropName(r.crop_id)} — مؤشر الجدوى {num(r.evi, 0)} من ١٠٠</Body>
          <Body muted>صافي ربح متوقع للفدان {egp(r.expected_profit_egp_per_feddan)} (سعر {egp(r.expected_price_egp_per_kg)} للكيلو، تكلفة {egp(r.cost_egp_per_feddan)} للفدان)</Body>
        </View>
      ))}
    </Card>
  );
}

const STATUS: Record<string, string> = { planned: 'ناوي أزرعه', planted: 'اتزرع', harvested: 'اتحصد' };

function Plans({ plot, intentions, market, cropName, onSaved }: {
  plot: Plot; intentions: Intention[]; market: Market; cropName: (id: string) => string; onSaved: () => void;
}) {
  const next = nextSeason();
  const [crop, setCrop] = useState<string | null>(null);
  const [area, setArea] = useState('');
  const [msg, setMsg] = useState('');
  const seasonal = market.crops.filter((c) => c.seasons.includes(next.season));

  async function add() {
    const a = parseNum(area);
    if (!crop) return setMsg('اختار المحصول.');
    if (!a || a <= 0 || a > plot.area_feddan) return setMsg(`اكتب المساحة بالفدان (لحد ${num(plot.area_feddan)}).`);
    const { error } = await supabase.from('intentions').insert({ plot_id: plot.id, crop_id: crop, season: next.season, year: next.year, area_feddan: a });
    setMsg(error ? 'حصلت مشكلة في الحفظ، حاول تاني.' : 'اتسجّل.');
    if (!error) { setCrop(null); setArea(''); onSaved(); }
  }

  async function setStatus(id: number, status: string) {
    await supabase.from('intentions').update({ status }).eq('id', id);
    onSaved();
  }

  return (
    <Card>
      <H2>هتزرع إيه الموسم {SEASON[next.season]} {yr(next.year)}؟</H2>
      <Body muted>تسجيل نيتك بيساعد كل المزارعين يشوفوا الصورة الكاملة (بنعرض المجموع بس، مش بيانات حد بعينه).</Body>
      <Chips>{seasonal.map((c) => <Chip key={c.id} label={c.name_ar} selected={crop === c.id} onPress={() => setCrop(c.id)} />)}</Chips>
      <Field label="المساحة (فدان)" value={area} onChangeText={setArea} keyboardType="numeric" />
      {msg ? <Body>{msg}</Body> : null}
      <Button label="سجّل" onPress={add} />
      {intentions.map((i) => (
        <View key={i.id} style={{ gap: 6, paddingTop: 10 }}>
          <Body>{cropName(i.crop_id)} · {SEASON[i.season]} {yr(i.year)} · {num(i.area_feddan)} فدان · {STATUS[i.status]}</Body>
          {i.status === 'planned' ? <Button label="زرعته" secondary onPress={() => setStatus(i.id, 'planted')} /> : null}
          {i.status === 'planted' ? <Button label="حصدته" secondary onPress={() => setStatus(i.id, 'harvested')} /> : null}
          {i.status === 'harvested' && !i.harvest ? <HarvestForm intentionId={i.id} onSaved={onSaved} /> : null}
          {i.harvest ? <Body muted>المحصول: {num(i.harvest.yield_t)} طن. شكراً، ده بيحسّن التوقعات.</Body> : null}
        </View>
      ))}
    </Card>
  );
}

function HarvestForm({ intentionId, onSaved }: { intentionId: number; onSaved: () => void }) {
  const [yieldT, setYieldT] = useState('');
  const [price, setPrice] = useState('');
  const [msg, setMsg] = useState('');

  async function save() {
    const y = parseNum(yieldT);
    const p = price ? parseNum(price) : null;
    if (y == null) return setMsg('اكتب كمية المحصول بالطن.');
    if (price && p == null) return setMsg('اكتب السعر بالأرقام بس.');
    const { error } = await supabase.from('harvest_reports').insert({ intention_id: intentionId, yield_t: y, price_egp_per_kg: p });
    setMsg(error ? 'حصلت مشكلة في الحفظ، حاول تاني.' : '');
    if (!error) onSaved();
  }

  return (
    <View style={{ gap: 8 }}>
      <Field label="الكمية اللي حصدتها (طن)" value={yieldT} onChangeText={setYieldT} keyboardType="numeric" />
      <Field label="السعر اللي بعت بيه (جنيه للكيلو)" value={price} onChangeText={setPrice} keyboardType="numeric" />
      {msg ? <Body>{msg}</Body> : null}
      <Button label="سجّل الحصاد" onPress={save} />
    </View>
  );
}
