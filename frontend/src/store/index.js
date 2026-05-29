import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      email: null,
      setAuth: ({ token, email }) => set({ token, email }),
      logout: () => set({ token: null, email: null }),
    }),
    { name: "daysim-auth" }
  )
);

export const useTradeStore = create((set) => ({
  symbol: "BTC-USDT",
  timeframe: "1m",
  lastPrice: null,
  account: null,
  positions: [],
  orders: [],
  trades: [],
  setSymbol: (symbol) => set({ symbol }),
  setTimeframe: (timeframe) => set({ timeframe }),
  setLastPrice: (lastPrice) => set({ lastPrice }),
  setAccount: (account) => set({ account }),
  setPositions: (positions) => set({ positions }),
  setOrders: (orders) => set({ orders }),
  setTrades: (trades) => set({ trades }),
}));
