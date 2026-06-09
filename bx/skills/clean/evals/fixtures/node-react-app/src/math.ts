export function add(a: number, b: number): number {
  return a + b;
}

function unusedCalc(values: number[]): number {
  return values.reduce((acc, v) => acc * v, 1);
}
