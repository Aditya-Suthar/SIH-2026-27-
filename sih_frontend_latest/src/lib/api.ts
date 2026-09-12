import { useCallback, useEffect, useRef, useState } from "react";
import {API_BASE_URL as base} from "./config";
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}
function expireSession() {
  ['access_token', 'isLoggedIn', 'role', 'name', 'email'].forEach(key => localStorage.removeItem(key));
  window.dispatchEvent(new Event('sahas-session-expired'));
  window.location.replace('/login');
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("access_token");
  if (!token) { expireSession(); throw new ApiError("Please sign in again.", 401); }
  const response = await fetch(`${base}${path}`, { ...options, headers: {
    "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...options.headers,
  } });
  if (!response.ok) {
    if (response.status === 401 && localStorage.getItem('access_token') === token) expireSession();
    const detail = await response.json().catch(()=>null);
    const message = response.status === 401 ? "Your session expired. Please sign in again."
      : response.status === 403 ? "Access denied for this section."
      : response.status === 404 ? "This section or record is unavailable."
      : response.status === 409 ? (typeof detail?.detail === "string" ? detail.detail : "The request conflicts with the current case state.")
      : response.status === 422 ? "Check the entered values and try again." : "Could not complete the request. Please try again.";
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
export function useRemote<T>(path: string, interval = 15000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const controller = useRef<AbortController | null>(null);
  const loaded = useRef(false);
  const refresh = useCallback(async () => {
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    try {
      const result = await api<T>(path, { signal: request.signal });
      if (!request.signal.aborted) { setData(result); setError(""); loaded.current = true; }
    } catch (e) {
      if (!request.signal.aborted) {
        const message = e instanceof Error ? e.message : "Unable to load data.";
        setError(`${loaded.current ? "Refresh failed. " : ""}${message}`);
        if (e instanceof ApiError && [401, 403, 404].includes(e.status)) setData(null);
      }
    } finally { if (!request.signal.aborted) setLoading(false); }
  }, [path]);
  useEffect(() => {
    loaded.current = false; setData(null); setError(""); setLoading(true); void refresh();
    const clear = () => { controller.current?.abort(); setData(null); setLoading(false); };
    window.addEventListener('sahas-session-expired', clear);
    const timer = window.setInterval(() => { if (!document.hidden) void refresh(); }, interval);
    return () => { clearInterval(timer); controller.current?.abort(); window.removeEventListener('sahas-session-expired', clear); };
  }, [refresh, interval]);
  return { data, error, loading, refresh };
}
