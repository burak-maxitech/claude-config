import { useState, useEffect } from 'react';
import clsx from 'clsx';

interface Props {
  onClick: () => void;
}

export function Button({ onClick }: Props) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      className={clsx('btn', { 'btn-hover': hovered })}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onClick}
    >
      Click
    </button>
  );
}
