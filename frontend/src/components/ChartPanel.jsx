import { createChart } from "lightweight-charts";
import { useCallback, useEffect, useRef } from "react";

import { useMarketWS } from "../hooks/useMarketWS";
import { useTradeStore } from "../store";

export default function ChartPanel() {
  const containerRef = useRef(null);
  const seriesRef = useRef(null);
  const chartRef = useRef(null);

  const symbol = useTradeStore((s) => s.symbol);
  const timeframe = useTradeStore((s) => s.timeframe);
  const setSymbol = useTradeStore((s) => s.setSymbol);
  const setTimeframe = useTradeStore((s) => s.setTimeframe);
  const lastPrice = useTradeStore((s) => s.lastPrice);

  useEffect(() => {
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0f1320" }, textColor: "#d1d5db" },
      grid: { vertLines: { color: "#1f2530" }, horzLines: { color: "#1f2530" } },
      timeScale: { timeVisible: true, borderColor: "#1f2530" },
      rightPriceScale: { borderColor: "#1f2530" },
      autoSize: true,
    });
    const series = chart.addCandlestickSeries({
      upColor: "#16c784",
      downColor: "#ea3943",
      borderVisible: false,
      wickUpColor: "#16c784",
      wickDownColor: "#ea3943",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => chart.remove();
  }, []);

  // Clear stale candles immediately when symbol or timeframe changes,
  // before the new WS snapshot arrives.
  useEffect(() => {
    seriesRef.current?.setData([]);
  }, [symbol, timeframe]);

  const onSnapshot = useCallback((candles) => {
    seriesRef.current?.setData(candles);
  }, []);
  const onCandle = useCallback((candle) => {
    seriesRef.current?.update(candle);
  }, []);

  useMarketWS({ onSnapshot, onCandle });

  const SYMBOLS = [
    "BTC-USDT",  "ETH-USDT",  "BNB-USDT",  "SOL-USDT",  "XRP-USDT",
    "DOGE-USDT", "TON-USDT",  "ADA-USDT",  "TRX-USDT",  "AVAX-USDT",
    "SHIB-USDT", "LINK-USDT", "DOT-USDT",  "BCH-USDT",  "NEAR-USDT",
    "UNI-USDT",  "LTC-USDT",  "APT-USDT",  "ICP-USDT",  "SUI-USDT",
    "ETC-USDT",  "FIL-USDT",  "ARB-USDT",  "OP-USDT",   "ATOM-USDT",
    "VET-USDT",  "HBAR-USDT", "MKR-USDT",  "GRT-USDT",  "ALGO-USDT",
    "XLM-USDT",  "AAVE-USDT", "INJ-USDT",  "WLD-USDT",  "SEI-USDT",
    "EGLD-USDT", "CRV-USDT",  "LDO-USDT",  "PEPE-USDT", "FLOKI-USDT",
    "STX-USDT",  "IMX-USDT",  "MANA-USDT", "SAND-USDT", "EOS-USDT",
    "TIA-USDT",  "WIF-USDT",  "JUP-USDT",  "SNX-USDT",  "PYTH-USDT",
  ];
  const TIMEFRAMES = ["1m", "5m", "15m", "1H"];

  return (
    <div className="chart-panel">
      <div className="chart-toolbar">
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          {SYMBOLS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <div className="tf-group">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={tf === timeframe ? "tf active" : "tf"}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
        {lastPrice && <span className="last-price">{Number(lastPrice).toLocaleString()}</span>}
      </div>
      <div className="chart-canvas" ref={containerRef} />
    </div>
  );
}
