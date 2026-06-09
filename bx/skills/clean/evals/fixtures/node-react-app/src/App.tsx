import { useState } from 'react';
import axios from 'axios';
import clsx from 'clsx';
import { Button } from './components/Button';
import { formatDate } from './utils/format';
import { add } from './math';

const PLUGIN = 'analytics';

export function App() {
  const [count, setCount] = useState(0);
  const total = add(count, 1);
  const label = formatDate(new Date());

  async function refresh() {
    const res = await axios.get('/api/data');
    setCount(res.data.count);
    const mod = await import(`./plugins/${PLUGIN}`);
    mod.track('refresh');
  }

  return (
    <div className={clsx('card')}>
      <h1 className="btn">{label}: {total}</h1>
      <Button onClick={refresh} />
    </div>
  );
}
