import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { Product } from "../types/product";

export function useProducts(category?: string) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    api
      .getProducts({ category })
      .then((res) => setProducts(res.items))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { products, loading, error, reload };
}
