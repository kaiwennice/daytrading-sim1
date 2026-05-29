import { useEffect } from "react";

import { useTradeStore } from "../store";

export function useMarketWS({ onSnapshot, onCandle }) {
  const symbol = useTradeStore((s) => s.symbol);
  const timeframe = useTradeStore((s) => s.timeframe);
  const setLastPrice = useTradeStore((s) => s.setLastPrice);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/market?symbol=${symbol}&timeframe=${timeframe}`;
    const ws = new WebSocket(url);

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") {
        onSnapshot(msg.candles);
        if (msg.candles.length) setLastPrice(msg.candles[msg.candles.length - 1].close);
      } else if (msg.type === "candle") {
        onCandle(msg.candle);
        setLastPrice(msg.candle.close);
      }
    };

    return () => ws.close();
  }, [symbol, timeframe, onSnapshot, onCandle, setLastPrice]);
}
