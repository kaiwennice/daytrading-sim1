import client from "./client";

export const placeOrder = (payload) => client.post("/orders", payload).then((r) => r.data);
export const listOrders = () => client.get("/orders").then((r) => r.data);
export const cancelOrder = (id) => client.delete(`/orders/${id}`).then((r) => r.data);
export const getAccount = () => client.get("/account").then((r) => r.data);
export const listTrades = () => client.get("/account/trades").then((r) => r.data);
export const listPositions = () => client.get("/account/positions").then((r) => r.data);
