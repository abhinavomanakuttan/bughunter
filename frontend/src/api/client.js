/**
 * BugHunter API Client
 * Wraps REST and SSE endpoints for frontend communication.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function validateUrl(url) {
  const res = await fetch(`${API_BASE}/validate-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error('Validation request failed');
  return res.json();
}

export async function startScan(config) {
  const res = await fetch(`${API_BASE}/scans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to start scan (${res.status})`);
  }
  return res.json();
}

export async function listScans(limit = 50) {
  const res = await fetch(`${API_BASE}/scans?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch scans');
  return res.json();
}

export async function getScan(scanId) {
  const res = await fetch(`${API_BASE}/scans/${scanId}`);
  if (!res.ok) throw new Error(`Failed to fetch scan ${scanId}`);
  return res.json();
}

export async function getFindings(scanId) {
  const res = await fetch(`${API_BASE}/scans/${scanId}/findings`);
  if (!res.ok) throw new Error(`Failed to fetch findings for ${scanId}`);
  return res.json();
}

export function subscribeScanEvents(scanId, onMessage, onError) {
  const eventSource = new EventSource(`${API_BASE}/scans/${scanId}/stream`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (err) {
      console.warn('Failed to parse SSE payload:', err, event.data);
    }
  };

  eventSource.onerror = (err) => {
    if (onError) onError(err);
    eventSource.close();
  };

  return () => eventSource.close();
}
