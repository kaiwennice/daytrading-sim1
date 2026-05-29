import client from "./client";

export const getSymbols = () => client.get("/market/symbols").then((r) => r.data);
export const getCandles = (symbol, timeframe, limit = 300) =>
  client
    .get("/market/candles", { params: { symbol, timeframe, limit } })
    .then((r) => r.data);
