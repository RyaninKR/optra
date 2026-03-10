import { useCallback, useEffect, useState } from "react";

interface ServiceStatus {
  connected: boolean;
  team?: string;
  workspace?: string;
}

interface AuthStatus {
  slack: ServiceStatus;
  notion: ServiceStatus;
}

const DEFAULT: AuthStatus = {
  slack: { connected: false },
  notion: { connected: false },
};

export function useAuth() {
  const [status, setStatus] = useState<AuthStatus>(DEFAULT);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasAnyConnection = status.slack.connected || status.notion.connected;

  return { status, loading, refresh, hasAnyConnection };
}
