import { useTradeStore } from "../store";

export default function TradeHistory() {
  const trades = useTradeStore((s) => s.trades);
  return (
    <div className="trade-history">
      <h4>成交记录</h4>
      <table>
        <thead><tr><th>时间</th><th>品种</th><th>方向</th><th>数量</th><th>价格</th><th>盈亏</th></tr></thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id}>
              <td>{new Date(t.executed_at).toLocaleTimeString()}</td>
              <td>{t.symbol}</td>
              <td className={t.side === "buy" ? "up" : "down"}>{t.side}</td>
              <td>{t.quantity}</td>
              <td>{Number(t.price).toLocaleString()}</td>
              <td className={Number(t.realized_pnl) >= 0 ? "up" : "down"}>
                {t.realized_pnl != null ? Number(t.realized_pnl).toFixed(2) : "-"}
              </td>
            </tr>
          ))}
          {trades.length === 0 && <tr><td colSpan={6} className="empty">暂无成交</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
