// Runs the migration + seed in an in-process Postgres (PGlite) with a minimal stand-in for
// Supabase's auth schema and roles, then checks row-level security. No Docker needed.
import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';

const dir = new URL('../', import.meta.url);
const read = (p) => readFileSync(new URL(p, dir), 'utf8');

const SUPABASE_STUB = `
  create role anon nologin;
  create role authenticated nologin;
  create role service_role nologin bypassrls;
  create schema auth;
  create table auth.users (id uuid primary key, phone text);
  create function auth.uid() returns uuid language sql stable
    as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  grant usage on schema auth to anon, authenticated;
  grant usage on schema public to anon, authenticated;
`;

const A = '00000000-0000-0000-0000-00000000000a';
const B = '00000000-0000-0000-0000-00000000000b';
let db;

// Run fn as an API caller: role 'anon', or 'authenticated' with the given user id.
async function as(role, uid, fn) {
  await db.exec(`set role ${role}`);
  await db.query(`select set_config('request.jwt.claim.sub', $1, false)`, [uid ?? '']);
  try { return await fn(); } finally { await db.exec('reset role'); }
}

before(async () => {
  db = new PGlite();
  await db.exec(SUPABASE_STUB);
  for (const f of readdirSync(new URL('migrations/', dir)).sort()) await db.exec(read(`migrations/${f}`));
  await db.exec(read('seed.sql'));
  await db.exec(`insert into auth.users (id) values ('${A}'), ('${B}')`);
});

test('seed loads all governorates and crops', async () => {
  assert.equal((await db.query('select count(*)::int n from governorates')).rows[0].n, 27);
  assert.equal((await db.query('select count(*)::int n from crops')).rows[0].n, 17);
});

test('anon can read public data but not farmer data, and cannot write', async () => {
  await as('anon', null, async () => {
    assert.equal((await db.query('select count(*)::int n from crops')).rows[0].n, 17);
    await assert.rejects(db.query('select * from farmers'), /permission denied/);
    await assert.rejects(db.query(`insert into crops values ('x','x','x','field','{winter}','low','{clay}',1)`), /permission denied/);
  });
});

test('farmers only see and change their own rows', async () => {
  const plotA = await as('authenticated', A, async () => {
    await db.query(`insert into farmers (id, gov_id) values ($1, 'sharqia')`, [A]);
    const plot = (await db.query(`insert into plots (area_feddan, soil) values (3, 'clay') returning id`)).rows[0].id;
    const intent = (await db.query(
      `insert into intentions (plot_id, crop_id, season, year, area_feddan) values ($1, 'tomato', 'summer', 2027, 2) returning id`,
      [plot])).rows[0].id;
    await db.query(`insert into harvest_reports (intention_id, yield_t) values ($1, 40)`, [intent]);
    return plot;
  });

  await as('authenticated', B, async () => {
    await db.query(`insert into farmers (id) values ($1)`, [B]);
    for (const t of ['farmers', 'plots', 'intentions', 'harvest_reports']) {
      const others = (await db.query(`select count(*)::int n from ${t}`)).rows[0].n;
      assert.equal(others, t === 'farmers' ? 1 : 0, `B sees A's ${t}`);
    }
    await assert.rejects(db.query(`insert into plots (farmer_id, area_feddan) values ($1, 1)`, [A]), /row-level security/);
    await assert.rejects(
      db.query(`insert into intentions (plot_id, crop_id, season, year, area_feddan) values ($1, 'potato', 'winter', 2027, 1)`, [plotA]),
      /row-level security/);
    await assert.rejects(db.query(`insert into farmers (id) values ($1)`, [A]), /row-level security|duplicate key/);
    const upd = await db.query(`update plots set area_feddan = 99 where id = $1`, [plotA]);
    assert.equal(upd.affectedRows, 0);
  });
});

test('unit and range checks reject bad rows', async () => {
  await assert.rejects(db.query(`insert into crop_stats (crop_id, year, area_feddan, source) values ('tomato', 2024, -1, 't')`), /check/);
  await assert.rejects(db.query(`insert into trade (crop_id, year, month, source) values ('tomato', 2024, 13, 't')`), /check/);
  // national row (gov_id null) is unique per crop/season/year/source
  await db.query(`insert into crop_stats (crop_id, year, area_feddan, source) values ('wheat', 2024, 1, 't')`);
  await assert.rejects(db.query(`insert into crop_stats (crop_id, year, area_feddan, source) values ('wheat', 2024, 2, 't')`), /duplicate key/);
});
