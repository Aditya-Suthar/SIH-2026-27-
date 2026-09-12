import { API_BASE_URL } from './config';

export async function transcribeVoice(audio: Blob, signal?: AbortSignal) {
  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('Please sign in again.');
  if (!API_BASE_URL) throw new Error('Voice API is not configured. Set VITE_API_BASE_URL and rebuild the frontend.');
  const url = `${API_BASE_URL}/api/victim/voice/transcribe`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': audio.type || 'audio/webm' },
      body: audio,
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(`Voice request could not reach ${url}. No HTTP status was available. Check the backend availability, HTTPS, and CORS permission for ${window.location.origin}.`);
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail
      : Array.isArray(payload?.detail) ? payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('; ')
      : response.status === 401 ? 'Your session expired. Please sign in again.'
      : response.status === 404 ? 'Voice route is unavailable on the deployed backend.'
      : response.status === 502 || response.status === 503 ? 'Backend or transcription service is unavailable. Check deployment logs.'
      : response.status === 504 ? 'The backend timed out during transcription.'
      : response.statusText || 'Voice transcription failed.';
    throw new Error(`Voice request failed (HTTP ${response.status}): ${detail}`);
  }
  if (typeof payload?.transcript !== 'string') throw new Error('Voice API returned an invalid response. Check that VITE_API_BASE_URL points to FastAPI.');
  const transcript = payload.transcript.trim();
  if (!transcript) throw new Error('No speech could be detected. Please try recording again.');
  return { transcript, language: typeof payload.language === 'string' ? payload.language : null };
}
