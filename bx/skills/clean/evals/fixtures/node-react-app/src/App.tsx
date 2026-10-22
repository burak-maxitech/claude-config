import { useState } from 'react';
import axios from 'axios';
import clsx from 'clsx';
import { Button } from './components/Button';
import { formatDate } from './utils/format';
import { capitalize } from './utils/strings';
import { add } from './math';
import { t } from './i18n';
import { ENABLE_NEW_CHECKOUT, FLAGS } from './flags';
import type { User, Status } from './types';

const PLUGIN = 'analytics';

export function App() {
  const [count, setCount] = useState(0);
  const [status, setStatus] = useState<Status>('idle');
  const total = add(count, 1);
  const label = formatDate(new Date());
  const user: User = { id: 'u1', name: capitalize('guest') };

  async function refresh() {
    setStatus('busy');
    try {
      const res = await axios.get('/api/data');
      setCount(res.data.count);
      const mod = await import(`./plugins/${PLUGIN}`);
      mod.track('refresh');
    } catch (err: unknown) {
      const code = (err as { code?: string }).code ?? 'timeout';
      console.error(t(`error.${code}`));
    } finally {
      setStatus('idle');
    }
  }

  const checkout = ENABLE_NEW_CHECKOUT ? 'checkout-v2' : 'checkout-v1';

  return (
    <div className={clsx('card')}>
      <h1 className="btn">{t('greeting')}, {user.name}</h1>
      <p>{label}: {total} ({status}) via {checkout}{FLAGS.beta ? ' [beta]' : ''}</p>
      <Button onClick={refresh} />
    </div>
  );
}
