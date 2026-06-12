import { useState, useCallback } from 'react';
import { api } from '@/api';

const POLL_INTERVAL = 2000;
const MAX_POLLS     = 150; // 5 minutes

export function useBuild() {
  const [building, setBuilding] = useState(false);

  const buildExe = useCallback(async (wfId, { onSuccess, onError } = {}) => {
    setBuilding(true);
    let jobId;
    try {
      const data = await api('POST', `/api/workflows/${wfId}/build`);
      jobId = data.job_id;
    } catch (e) {
      setBuilding(false);
      onError?.(`Could not start build: ${e.message}`);
      return;
    }

    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL));
      let status;
      try {
        status = await api('GET', `/api/workflows/${wfId}/build/status/${jobId}`);
      } catch (e) {
        setBuilding(false);
        onError?.(`Network error while polling: ${e.message}`);
        return;
      }
      if (status.status === 'running') continue;
      setBuilding(false);
      if (status.status === 'success') {
        onSuccess?.(status);
      } else {
        onError?.([status.error, status.log].filter(Boolean).join('\n\n'), status.log);
      }
      return;
    }
    setBuilding(false);
    onError?.('Build timed out (> 5 minutes).');
  }, []);

  return { building, buildExe };
}
