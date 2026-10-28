-- Nabta initial schema: reference data, market statistics, farmer data, computed outputs.
-- Units are normalised on import: area in feddan, quantities in tonnes, prices in EGP/kg.

create type season as enum ('winter', 'summer', 'nili', 'perennial');
create type soil_type as enum ('clay', 'loam', 'sandy', 'calcareous', 'saline');
create type water_source as enum ('canal', 'well', 'mixed');
create type price_granularity as enum ('day', 'month', 'year');
create type intention_status as enum ('planned', 'planted', 'harvested');
create type market_outlook as enum ('surplus', 'balanced', 'deficit');

-- ---------------------------------------------------------------- reference

create table governorates (
  id      text primary key,
  name_ar text not null,
  name_en text not null,
  -- Ministry of Agriculture statistical grouping
  region  text not null check (region in ('lower', 'middle', 'upper', 'frontier'))
);

create table markaz (
  id      int generated always as identity primary key,
  gov_id  text not null references governorates,
  name_ar text not null,
  name_en text,
  unique (gov_id, name_ar)
);

create table crops (
  id          text primary key,
  name_ar     text not null,
  name_en     text not null,
  category    text not null check (category in ('vegetable', 'field', 'fruit')),
  seasons     season[] not null,
  water_need  text not null check (water_need in ('low', 'medium', 'high')),
  soils       soil_type[] not null,
  cycle_days  smallint check (cycle_days > 0)
);

-- ---------------------------------------------------------------- statistics (written by import jobs)

-- gov_id null = national total; season null = all seasons of the year combined.
create table crop_stats (
  id                 bigint generated always as identity primary key,
  crop_id            text not null references crops,
  gov_id             text references governorates,
  season             season,
  year               smallint not null,
  area_feddan        numeric check (area_feddan >= 0),
  production_t       numeric check (production_t >= 0),
  yield_t_per_feddan numeric check (yield_t_per_feddan >= 0),
  source             text not null,
  published_at       date,
  unique nulls not distinct (crop_id, gov_id, season, year, source)
);

-- market: 'obour' (wholesale), 'farmgate' (producer price), etc.
create table prices (
  id             bigint generated always as identity primary key,
  crop_id        text not null references crops,
  market         text not null,
  price_date     date not null,
  granularity    price_granularity not null,
  min_egp_per_kg numeric check (min_egp_per_kg >= 0),
  max_egp_per_kg numeric check (max_egp_per_kg >= 0),
  avg_egp_per_kg numeric not null check (avg_egp_per_kg >= 0),
  source         text not null,
  unique (crop_id, market, price_date, granularity, source)
);

create table costs (
  id                  bigint generated always as identity primary key,
  crop_id             text not null references crops,
  gov_id              text references governorates,
  year                smallint not null,
  seeds_egp           numeric,
  fertiliser_egp      numeric,
  pesticide_egp       numeric,
  labour_egp          numeric,
  irrigation_egp      numeric,
  total_egp_per_feddan numeric not null check (total_egp_per_feddan >= 0),
  source              text not null,
  unique nulls not distinct (crop_id, gov_id, year, source)
);

-- month null = yearly total.
create table trade (
  id        bigint generated always as identity primary key,
  crop_id   text not null references crops,
  year      smallint not null,
  month     smallint check (month between 1 and 12),
  export_t  numeric check (export_t >= 0),
  import_t  numeric check (import_t >= 0),
  source    text not null,
  unique nulls not distinct (crop_id, year, month, source)
);

-- ---------------------------------------------------------------- farmer data (phone number lives in auth.users)

create table farmers (
  id               uuid primary key references auth.users on delete cascade,
  full_name        text,
  gov_id           text references governorates,
  markaz_id        int references markaz,
  capital_egp      numeric check (capital_egp >= 0),
  experience_years smallint check (experience_years >= 0),
  created_at       timestamptz not null default now()
);

create table plots (
  id           bigint generated always as identity primary key,
  farmer_id    uuid not null default auth.uid() references farmers on delete cascade,
  area_feddan  numeric not null check (area_feddan > 0),
  soil         soil_type,
  water_source water_source,
  gov_id       text references governorates,
  markaz_id    int references markaz,
  created_at   timestamptz not null default now()
);
create index on plots (farmer_id);

create table intentions (
  id          bigint generated always as identity primary key,
  plot_id     bigint not null references plots on delete cascade,
  crop_id     text not null references crops,
  season      season not null,
  year        smallint not null,
  area_feddan numeric not null check (area_feddan > 0),
  status      intention_status not null default 'planned',
  created_at  timestamptz not null default now()
);
create index on intentions (plot_id);
create index on intentions (crop_id, season, year);

create table harvest_reports (
  id               bigint generated always as identity primary key,
  intention_id     bigint not null unique references intentions on delete cascade,
  yield_t          numeric not null check (yield_t >= 0),
  price_egp_per_kg numeric check (price_egp_per_kg >= 0),
  sold_on          date,
  created_at       timestamptz not null default now()
);

-- ---------------------------------------------------------------- computed outputs (written by analytics jobs)

create table forecasts (
  id                 bigint generated always as identity primary key,
  crop_id            text not null references crops,
  market             text not null,
  target_month       date not null,
  price_egp_per_kg   numeric not null,
  lower_egp_per_kg   numeric,
  upper_egp_per_kg   numeric,
  model              text not null,
  run_at             timestamptz not null default now(),
  unique (crop_id, market, target_month, model, run_at)
);

-- The "quad dashboard". gov_id null = national. Built only from aggregates (min 10 farms per cell).
create table dashboard_cells (
  crop_id            text not null references crops,
  season             season not null,
  year               smallint not null,
  gov_id             text references governorates,
  area_now_feddan    numeric,
  expected_prod_t    numeric,
  last_year_prod_t   numeric,
  demand_t           numeric,
  gap_pct            numeric,
  outlook            market_outlook,
  updated_at         timestamptz not null default now(),
  unique nulls not distinct (crop_id, season, year, gov_id)
);

create table recommendations (
  id                       bigint generated always as identity primary key,
  farmer_id                uuid not null references farmers on delete cascade,
  plot_id                  bigint not null references plots on delete cascade,
  season                   season not null,
  year                     smallint not null,
  crop_id                  text not null references crops,
  rank                     smallint not null,
  evi                      numeric not null check (evi between 0 and 100),
  expected_profit_egp_per_feddan numeric,
  risk                     numeric,
  run_at                   timestamptz not null default now()
);
create index on recommendations (farmer_id, season, year);

-- ---------------------------------------------------------------- access
-- Writes to reference/statistics/computed tables happen only with the service role (bypasses RLS).

alter table governorates    enable row level security;
alter table markaz          enable row level security;
alter table crops           enable row level security;
alter table crop_stats      enable row level security;
alter table prices          enable row level security;
alter table costs           enable row level security;
alter table trade           enable row level security;
alter table forecasts       enable row level security;
alter table dashboard_cells enable row level security;
alter table farmers         enable row level security;
alter table plots           enable row level security;
alter table intentions      enable row level security;
alter table harvest_reports enable row level security;
alter table recommendations enable row level security;

-- Public data: readable before sign-in.
grant select on governorates, markaz, crops, crop_stats, prices, costs, trade, forecasts, dashboard_cells
  to anon, authenticated;
create policy "public read" on governorates    for select to anon, authenticated using (true);
create policy "public read" on markaz          for select to anon, authenticated using (true);
create policy "public read" on crops           for select to anon, authenticated using (true);
create policy "public read" on crop_stats      for select to anon, authenticated using (true);
create policy "public read" on prices          for select to anon, authenticated using (true);
create policy "public read" on costs           for select to anon, authenticated using (true);
create policy "public read" on trade           for select to anon, authenticated using (true);
create policy "public read" on forecasts       for select to anon, authenticated using (true);
create policy "public read" on dashboard_cells for select to anon, authenticated using (true);

-- Farmer data: each farmer sees and edits only their own rows.
grant select, insert, update on farmers to authenticated;
grant select, insert, update, delete on plots, intentions, harvest_reports to authenticated;
grant select on recommendations to authenticated;

create policy "own profile" on farmers for all to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy "own plots" on plots for all to authenticated
  using (farmer_id = (select auth.uid())) with check (farmer_id = (select auth.uid()));

create policy "own intentions" on intentions for all to authenticated
  using (exists (select 1 from plots p where p.id = plot_id and p.farmer_id = (select auth.uid())))
  with check (exists (select 1 from plots p where p.id = plot_id and p.farmer_id = (select auth.uid())));

create policy "own harvest reports" on harvest_reports for all to authenticated
  using (exists (
    select 1 from intentions i join plots p on p.id = i.plot_id
    where i.id = intention_id and p.farmer_id = (select auth.uid())))
  with check (exists (
    select 1 from intentions i join plots p on p.id = i.plot_id
    where i.id = intention_id and p.farmer_id = (select auth.uid())));

create policy "own recommendations" on recommendations for select to authenticated
  using (farmer_id = (select auth.uid()));
