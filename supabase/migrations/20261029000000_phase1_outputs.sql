-- Phase 1 outputs: dashboard cells carry the numbers the comparison screen needs, and
-- recommendations carry the inputs behind each score so the app can show "why".

-- Official statistics are yearly (no season split yet): season null = whole year.
alter table dashboard_cells alter column season drop not null;
alter table dashboard_cells
  add column data_year              smallint,  -- latest statistics year the cell is built on
  add column yield_t_per_feddan     numeric,
  add column price_egp_per_kg       numeric,   -- forecast farmgate price at the next harvest
  add column revenue_egp_per_feddan numeric;

alter table recommendations
  add column expected_price_egp_per_kg numeric,
  add column yield_t_per_feddan        numeric,
  add column cost_egp_per_feddan       numeric;
create index on recommendations (plot_id);
create index on recommendations (crop_id);
