// frontend/src/hooks/useLeagueBounds.ts
import { useState, useEffect } from "react";

export interface LeagueBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function useLeagueBounds(): LeagueBounds | null {
  const [bounds, setBounds] = useState<LeagueBounds | null>(null);

  useEffect(() => {
    return window.riftBuddy?.onLeagueBounds?.((b) => setBounds(b));
  }, []);

  return bounds;
}
