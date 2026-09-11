import { useCallback, useEffect, useRef, useState } from "react";
import {API_BASE_URL as base} from "./config";
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token");
  if (!token) throw new Error("Please sign in again.");
  const response = await fetch(`${base}${path}`, { ...options, headers: {
    "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...options.headers,
  } });
  if (!response.ok) {
    const detail = await response.json().catch(()=>null);
    const message = response.status === 401 ? "Your session expired. Please sign in again."
      : response.status === 403 || response.status === 404 ? "This information is not available to your account."
      : response.status === 409 ? (typeof detail?.detail === "string" ? detail.detail : "The request conflicts with the current case state.")
      : response.status === 422 ? "Check the entered values and try again." : "Could not complete the request. Please try again.";
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export function useRemote<T>(path: string, interval = 15000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const controller = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    try {
      const result = await api<T>(path, { signal: request.signal });
      if (!request.signal.aborted) { setData(result); setError(""); }
    } catch (e) {
      if (!request.signal.aborted) setError(e instanceof Error ? e.message : "Unable to load data.");
    } finally { if (!request.signal.aborted) setLoading(false); }
  }, [path]);
  useEffect(() => {
    setData(null); setError(""); setLoading(true); void refresh();
    const timer = window.setInterval(() => { if (!document.hidden) void refresh(); }, interval);
    return () => { clearInterval(timer); controller.current?.abort(); };
  }, [refresh, interval]);
  return { data, error, loading, refresh };
}
