import { useCallback, useEffect, useRef, useState } from "react";

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
  const [connecting, setConnecting] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        return data as AuthStatus;
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const connect = useCallback(
    async (service: "slack" | "notion") => {
      setConnecting(service);

      try {
        const res = await fetch(`/api/auth/${service}/connect`);
        const data = await res.json();

        if (data.error) {
          setConnecting(null);
          return;
        }

        // Open OAuth popup
        const popup = window.open(data.auth_url, `optra-${service}-auth`, "width=600,height=700");

        // Poll for completion
        pollRef.current = setInterval(async () => {
          const updated = await refresh();
          if (updated && updated[service]?.connected) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setConnecting(null);
            popup?.close();
          }
        }, 2000);

        // Safety: stop polling after 3 minutes
        setTimeout(() => {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setConnecting(null);
          }
        }, 180_000);
      } catch {
        setConnecting(null);
      }
    },
    [refresh],
  );

  const disconnect = useCallback(
    async (service: "slack" | "notion") => {
      await fetch(`/api/auth/${service}`, { method: "DELETE" });
      await refresh();
    },
    [refresh],
  );

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const hasAnyConnection = status.slack.connected || status.notion.connected;

  return { status, loading, connecting, refresh, connect, disconnect, hasAnyConnection };
}
