export function slugify(text: string): string {
  return text.toLowerCase().replace(/\s+/g, '-');
}

export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + '…' : text;
}
