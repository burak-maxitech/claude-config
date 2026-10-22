export interface User {
  id: string;
  name: string;
}

export type Status = 'idle' | 'busy';

export interface LegacyOrder {
  orderId: string;
  v1Token: string;
  items: string[];
}
