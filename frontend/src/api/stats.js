import client from "./client";

export const getStats = () => client.get("/stats").then((r) => r.data);
