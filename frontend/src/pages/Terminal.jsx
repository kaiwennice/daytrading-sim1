import { useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import ChartPanel from "../components/ChartPanel.jsx";
import OrderPanel from "../components/OrderPanel.jsx";
import PositionPanel from "../components/PositionPanel.jsx";
import TradeHistory from "../components/TradeHistory.jsx";
import { getAccount, listOrders, listPositions, listTrades } from "../api/orders";
import { useAccountWS } from "../hooks/useAccountWS";
import { useAuthStore, useTradeStore } from "../store";

export default function Terminal() {
  const email = useAuthStore((s) => s.email);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const account = useTradeStore((s) => s.account);
  const { setAccount, setOrders, setPositions, setTrades } = useTradeStore.getState();

  const refresh = useCallback(async () => {
    const [acc, ords, pos, trs] = await Promise.all([
      getAccount(), listOrders(), listPositions(), listTrades(),
    ]);
    setAccount(acc);
    setOrders(ords);
    setPositions(pos);
    setTrades(trs);
  }, [setAccount, setOrders, setPositions, setTrades]);

  useEffect(() => { refresh().catch(() => {}); }, [refresh]);
  useAccountWS(useCallback(() => { refresh().catch(() => {}); }, [refresh]));

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div className="terminal">
      <header className="terminal-header">
        <span className="brand-sm">DaySim</span>
        <div className="account-box">
          {account && (
            <>
              <span className="balance">余额 ${Number(account.balance_usdt).toLocaleString()}</span>
              <span className="balance">权益 ${Number(account.total_equity).toLocaleString()}</span>
            </>
          )}
          <span className="email">{email}</span>
          <button className="link" onClick={handleLogout}>登出</button>
        </div>
      </header>
      <main className="terminal-body">
        <ChartPanel />
        <OrderPanel onPlaced={refresh} />
        <section className="bottom-panels">
          <PositionPanel onChange={refresh} />
          <TradeHistory />
        </section>
      </main>
    </div>
  );
}
