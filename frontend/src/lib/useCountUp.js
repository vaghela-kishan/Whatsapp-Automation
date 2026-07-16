import { useEffect, useRef, useState } from "react";

// Smoothly animates a number from 0 → target with an ease-out curve.
export function useCountUp(target = 0, { duration = 900, decimals = 0 } = {}) {
  const [value, setValue] = useState(0);
  const raf = useRef(null);
  const startTs = useRef(null);

  useEffect(() => {
    cancelAnimationFrame(raf.current);
    startTs.current = null;
    const from = 0;
    const to = Number(target) || 0;

    const tick = (ts) => {
      if (startTs.current === null) startTs.current = ts;
      const t = Math.min(1, (ts - startTs.current) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      setValue(from + (to - from) * eased);
      if (t < 1) raf.current = requestAnimationFrame(tick);
      else setValue(to);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, duration]);

  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}
