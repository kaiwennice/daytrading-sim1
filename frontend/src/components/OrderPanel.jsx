import { useState } from "react";

import { placeOrder } from "../api/orders";
import { useTradeStore } from "../store";

export default function OrderPanel({ onPlaced }) {
  const symbol = useTradeStore((s) => s.symbol);
  const lastPrice = useTradeStore((s) => s.lastPrice);
  const [side, setSide] = useState("buy");
  const [orderType, setOrderType] = useState("market");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [trigger, setTrigger] = useState("");
  const [error, setError] = useState("");
  const [leverage, setLeverage] = useState(1);

  const handleSideChange = (newSide) => {
    setSide(newSide);
    if (newSide === "sell") setLeverage(1);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = { symbol, side, order_type: orderType, quantity };
      if (orderType === "limit") payload.price = price;
      if (orderType === "stop_loss" || orderType === "take_profit") payload.trigger_price = trigger;
      if (side === "buy") payload.leverage = leverage;
      await placeOrder(payload);
      setQuantity("");
      setPrice("");
      setTrigger("");
      onPlaced?.();
    } catch (err) {
      setError(err.response?.data?.detail || "下单失败");
    }
  };

  return (
    <aside className="order-panel">
      <div className="side-toggle">
        <button className={side === "buy" ? "buy active" : "buy"} onClick={() => handleSideChange("buy")}>买入</button>
        <button className={side === "sell" ? "sell active" : "sell"} onClick={() => handleSideChange("sell")}>卖出</button>
      </div>
      <form onSubmit={submit}>
        <label>类型</label>
        <select value={orderType} onChange={(e) => setOrderType(e.target.value)}>
          <option value="market">市价</option>
          <option value="limit">限价</option>
          <option value="stop_loss">止损（卖）</option>
          <option value="take_profit">止盈（卖）</option>
        </select>

        <label>数量</label>
        <input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="0.00" required />

        {orderType === "limit" && (
          <>
            <label>限价</label>
            <input value={price} onChange={(e) => setPrice(e.target.value)} placeholder={lastPrice || ""} required />
          </>
        )}
        {(orderType === "stop_loss" || orderType === "take_profit") && (
          <>
            <label>触发价</label>
            <input value={trigger} onChange={(e) => setTrigger(e.target.value)} required />
          </>
        )}

        {side === "buy" && (orderType === "market" || orderType === "limit") && (
          <>
            <label>杠杆</label>
            <div className="leverage-group">
              {[1, 2, 3, 5, 10, 20, 50, 100].map((lv) => (
                <button
                  key={lv}
                  type="button"
                  className={leverage === lv ? "lv active" : "lv"}
                  onClick={() => setLeverage(lv)}
                >
                  {lv}x
                </button>
              ))}
            </div>
          </>
        )}

        {error && <div className="error">{error}</div>}
        <button type="submit" className={`submit ${side}`}>
          {side === "buy" ? "买入" : "卖出"} {symbol}
        </button>
      </form>
    </aside>
  );
}
