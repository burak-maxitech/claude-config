import en from './locales/en.json';

const table = en as Record<string, string>;

export function t(key: string): string {
  return table[key] ?? key;
}
