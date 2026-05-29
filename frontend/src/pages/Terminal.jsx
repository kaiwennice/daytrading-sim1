import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import ChartPanel from "../components/ChartPanel.jsx";
import client from "../api/client";
import { useAuthStore, useTradeStore } from "../store";

export default function Terminal() {
  const email = useAuthStore((s) => s.email);
  const logout = useAuthStore((s) => s.logout);
  const account = useTradeStore((s) => s.account);
  const setAccount = useTradeStore((s) => s.setAccount);
  const navigate = useNavigate();

  useEffect(() => {
    client.get("/account").then((r) => setAccount(r.data)).catch(() => {});
  }, [setAccount]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="terminal">
      <header className="terminal-header">
        <span className="brand-sm">DaySim</span>
        <div className="account-box">
          {account && (
            <span className="balance">
              余额: ${Number(account.balance_usdt).toLocaleString()} USDT
            </span>
          )}
          <span className="email">{email}</span>
          <button className="link" onClick={handleLogout}>登出</button>
        </div>
      </header>

      <main className="terminal-body">
        <ChartPanel />
        <aside className="panel order-placeholder">下单面板（Phase B）</aside>
        <section className="panel table-placeholder">持仓 / 成交（Phase B）</section>
      </main>
    </div>
  );
}
