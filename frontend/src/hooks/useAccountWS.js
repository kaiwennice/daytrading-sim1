import { useEffect } from "react";

import { useAuthStore } from "../store";

// Connects to /ws/account with the JWT and invokes onFill for each fill event.
export function useAccountWS(onFill) {
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (!token) return undefined;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/account?token=${token}`;
    const ws = new WebSocket(url);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "fill") onFill(msg);
    };
    return () => ws.close();
  }, [token, onFill]);
}
