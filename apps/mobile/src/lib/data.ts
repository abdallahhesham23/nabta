import { useEffect, useState } from 'react';

import { supabase } from './supabase';

export type Outlook = 'surplus' | 'balanced' | 'deficit';
export type Season = 'winter' | 'summer' | 'nili' | 'perennial';

export type Crop = {
  id: string; name_ar: string; category: 'vegetable' | 'field' | 'fruit';
  seasons: Season[]; soils: string[]; water_need: string; cycle_days: number | null;
};
export type Cell = {
  crop_id: string; data_year: number; area_now_feddan: number; expected_prod_t: number;
  last_year_prod_t: number; demand_t: number | null; gap_pct: number | null; outlook: Outlook | null;
  yield_t_per_feddan: number; price_egp_per_kg: number | null; revenue_egp_per_feddan: number | null;
};
export type MarketPrice = { crop_id: string; price_date: string; min_egp_per_kg: number; max_egp_per_kg: number };
export type Forecast = {
  target_month: string; price_egp_per_kg: number; lower_egp_per_kg: number; upper_egp_per_kg: number;
};
export type Governorate = { id: string; name_ar: string };
export type Market = {
  crops: Crop[]; cells: Record<string, Cell>; obour: Record<string, MarketPrice>; governorates: Governorate[];
};

const byCrop = <T extends { crop_id: string }>(rows: T[]) => Object.fromEntries(rows.map((r) => [r.crop_id, r]));

async function fetchMarket(): Promise<Market> {
  const [crops, cells, obour, govs] = await Promise.all([
    supabase.from('crops').select('id, name_ar, category, seasons, soils, water_need, cycle_days'),
    supabase.from('dashboard_cells').select('*').is('gov_id', null),
    supabase.from('prices').select('crop_id, price_date, min_egp_per_kg, max_egp_per_kg')
      .eq('market', 'obour').order('price_date', { ascending: true }),
    supabase.from('governorates').select('id, name_ar').order('name_ar'),
  ]);
  const error = crops.error ?? cells.error ?? obour.error ?? govs.error;
  if (error) throw new Error(error.message);
  return {
    crops: crops.data as Crop[],
    cells: byCrop(cells.data as Cell[]),
    obour: byCrop(obour.data as MarketPrice[]),  // ascending order: the last row per crop wins
    governorates: govs.data as Governorate[],
  };
}

let cache: Promise<Market> | null = null;

export function useMarket() {
  const [state, setState] = useState<{ data?: Market; error?: string }>({});
  useEffect(() => {
    cache ??= fetchMarket();
    cache.then((data) => setState({ data }), (e) => { cache = null; setState({ error: String(e.message ?? e) }); });
  }, []);
  return state;
}

export async function fetchForecast(cropId: string): Promise<Forecast[]> {
  const { data, error } = await supabase.from('forecasts')
    .select('target_month, price_egp_per_kg, lower_egp_per_kg, upper_egp_per_kg')
    .eq('crop_id', cropId).eq('market', 'farmgate').order('target_month');
  if (error) throw new Error(error.message);
  return data as Forecast[];
}

const PLANT_MONTH: Record<Exclude<Season, 'perennial'>, number> = { summer: 3, nili: 8, winter: 10 };

/** The season planting this month or the next one to come (same rule as analytics/model/evi.py). */
export function nextSeason(today = new Date()): { season: Season; year: number } {
  const month = today.getMonth() + 1;
  const starts = Object.entries(PLANT_MONTH).map(([s, m]) => ({
    season: s as Season, year: today.getFullYear() + (m < month ? 1 : 0), m,
  }));
  starts.sort((a, b) => a.year - b.year || a.m - b.m);
  return starts[0];
}
