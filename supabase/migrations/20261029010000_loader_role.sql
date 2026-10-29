-- A narrow login for the analytics jobs (analytics/load.py, publish.py), so they don't need the
-- postgres password. Its password is set outside migrations: alter role nabta_loader login password ...
create role nabta_loader nologin bypassrls;  -- reads every farm plot to compute recommendations
grant usage on schema public to nabta_loader;
grant select on governorates, markaz, crops, farmers, plots, intentions to nabta_loader;
grant select, insert, delete on crop_stats, prices, costs, trade, forecasts, dashboard_cells, recommendations
  to nabta_loader;
