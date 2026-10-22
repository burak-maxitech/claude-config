export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function shout(s: string): string {
  return s.toUpperCase() + '!';
}
