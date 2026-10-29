-- What app farmers plan to plant this season, per crop. Filled only when 10+ farms planned the crop,
-- so no single farm can be picked out; null otherwise.
alter table dashboard_cells
  add column intended_area_feddan numeric,
  add column intending_farms      int;
