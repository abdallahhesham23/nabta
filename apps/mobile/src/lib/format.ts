import type { Outlook, Season } from './data';
import { theme } from './theme';

export function num(n: number | null | undefined, digits = 1): string {
  return n == null ? '—' : new Intl.NumberFormat('ar-EG', { maximumFractionDigits: digits }).format(n);
}

export const yr = (y: number) => new Intl.NumberFormat('ar-EG', { useGrouping: false }).format(y);

/** Large quantities as "١٢٫٣ ألف" or "٧٫٤ مليون". */
export function big(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${num(n / 1_000_000, 1)} مليون`;
  if (n >= 1_000) return `${num(n / 1_000, n >= 100_000 ? 0 : 1)} ألف`;
  return num(n, 0);
}

export const egp = (n: number | null | undefined) => (n == null ? '—' : `${num(n, n < 100 ? 2 : 0)} ج`);

export const pct = (n: number | null | undefined) => (n == null ? '—' : `${n > 0 ? '+' : ''}${num(n, 1)}٪`);

export const dayMonth = (iso: string) =>
  new Intl.DateTimeFormat('ar-EG', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(iso));

export const monthName = (iso: string) =>
  new Intl.DateTimeFormat('ar-EG', { month: 'short', timeZone: 'UTC' }).format(new Date(iso));

/** Accepts Arabic-Indic or Western digits; returns null for anything that isn't a number. */
export function parseNum(s: string): number | null {
  const western = s.replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace('٫', '.').trim();
  if (!/^\d+(\.\d+)?$/.test(western)) return null;
  return Number(western);
}

export const OUTLOOK: Record<Outlook, { label: string; color: string; hint: string }> = {
  surplus: { label: 'فائض متوقع', color: theme.surplus, hint: 'المعروض المتوقع أعلى من اللي السوق بيستوعبه عادة، فالأسعار ممكن تنزل.' },
  balanced: { label: 'متوازن', color: theme.balanced, hint: 'المعروض المتوقع قريب من اللي السوق بيستوعبه عادة.' },
  deficit: { label: 'عجز متوقع', color: theme.deficit, hint: 'المعروض المتوقع أقل من المعتاد، وده ممكن يعني أسعار أحسن.' },
};

export const SEASON: Record<Season, string> = { winter: 'شتوي', summer: 'صيفي', nili: 'نيلي', perennial: 'معمّر' };
export const SOIL: Record<string, string> = {
  clay: 'طينية', loam: 'طميية', sandy: 'رملية', calcareous: 'جيرية', saline: 'ملحية',
};
export const WATER: Record<string, string> = { canal: 'ترعة', well: 'بئر', mixed: 'ترعة وبئر' };
