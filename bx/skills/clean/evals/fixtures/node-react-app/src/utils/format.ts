export function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// export function formatDateLegacy(d: Date): string {
//   const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
//   const m = months[d.getMonth()];
//   const day = d.getDate();
//   const year = d.getFullYear();
//   return `${m} ${day}, ${year}`;
// }
