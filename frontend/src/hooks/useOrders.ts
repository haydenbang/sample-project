import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { Order } from "../types/order";

export function useOrders(status?: string) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    api
      .getOrders({ status })
      .then((res) => setOrders(res.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [status]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { orders, loading, error, reload };
}
