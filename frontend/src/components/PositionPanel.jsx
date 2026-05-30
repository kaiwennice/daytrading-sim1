import { cancelOrder } from "../api/orders";
import { useTradeStore } from "../store";

export default function PositionPanel({ onChange }) {
  const positions = useTradeStore((s) => s.positions);
  const orders = useTradeStore((s) => s.orders);
  const lastPrice = useTradeStore((s) => s.lastPrice);

  const cancel = async (id) => {
    await cancelOrder(id);
    onChange?.();
  };

  return (
    <div className="pos-panel">
      <h4>持仓</h4>
      <table>
        <thead><tr><th>品种</th><th>数量</th><th>均价</th><th>浮动盈亏</th></tr></thead>
        <tbody>
          {positions.map((p) => {
            const mark = Number(lastPrice) || Number(p.avg_cost);
            const upnl = (mark - Number(p.avg_cost)) * Number(p.quantity);
            return (
              <tr key={p.symbol}>
                <td>{p.symbol}</td>
                <td>{p.quantity}</td>
                <td>{Number(p.avg_cost).toLocaleString()}</td>
                <td className={upnl >= 0 ? "up" : "down"}>{upnl.toFixed(2)}</td>
              </tr>
            );
          })}
          {positions.length === 0 && <tr><td colSpan={4} className="empty">无持仓</td></tr>}
        </tbody>
      </table>

      <h4>挂单</h4>
      <table>
        <thead><tr><th>方向</th><th>类型</th><th>数量</th><th>价格</th><th></th></tr></thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id}>
              <td className={o.side === "buy" ? "up" : "down"}>{o.side}</td>
              <td>{o.order_type}</td>
              <td>{o.quantity}</td>
              <td>{o.price || o.trigger_price}</td>
              <td><button className="link" onClick={() => cancel(o.id)}>撤</button></td>
            </tr>
          ))}
          {orders.length === 0 && <tr><td colSpan={5} className="empty">无挂单</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
