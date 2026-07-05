import { useState, useCallback } from 'react';
import { apiFetch, type ApiFetchOptions } from '../services/api';

export function useApi<T = any>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const request = useCallback(async (path: string, options?: ApiFetchOptions) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<T>(path, options);
      setData(res);
      return res;
    } catch (err: any) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, request };
}
export default useApi;
