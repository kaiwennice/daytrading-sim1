import { createChart } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

import { getStats } from "../api/stats";

export default function StatsModal({ onClose }) {
  const [stats, setStats] = useState(null);
  const chartRef = useRef(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (!stats || !chartRef.current) return undefined;
    const chart = createChart(chartRef.current, {
      layout: { background: { color: "#0f1320" }, textColor: "#d1d5db" },
      grid: { vertLines: { color: "#1f2530" }, horzLines: { color: "#1f2530" } },
      autoSize: true,
    });
    const series = chart.addLineSeries({ color: "#16c784" });
    series.setData(
      stats.equity_curve.map((p) => ({
        time: Math.floor(new Date(p.recorded_at).getTime() / 1000),
        value: Number(p.total_equity),
      }))
    );
    return () => chart.remove();
  }, [stats]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>交易绩效</h3>
          <button className="link" onClick={onClose}>关闭</button>
        </div>
        {stats && (
          <>
            <div className="metrics">
              <div><span>胜率</span><b>{(stats.win_rate * 100).toFixed(1)}%</b></div>
              <div><span>盈亏比</span><b>{stats.profit_loss_ratio?.toFixed(2) ?? "-"}</b></div>
              <div><span>已实现盈亏</span><b className={Number(stats.total_realized_pnl) >= 0 ? "up" : "down"}>{Number(stats.total_realized_pnl).toFixed(2)}</b></div>
              <div><span>平仓笔数</span><b>{stats.closed_count}</b></div>
            </div>
            <div className="equity-chart" ref={chartRef} />
          </>
        )}
      </div>
    </div>
  );
}
