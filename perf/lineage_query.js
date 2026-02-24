
import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 10,
  duration: "1m",
  thresholds: {
    http_req_duration: ["p(95)<500"],
  },
};

const QUERY_API = "http://host.docker.internal:5000";

export default function () {
  // 获取transactions
  const txResp = http.get(`${QUERY_API}/api/query/transactions`);
  
  if (txResp.status === 200) {
    const transactions = txResp.json();
    
    if (transactions && transactions.length > 0) {
      // 随机选择一个transaction查询lineage
      const randomTx = transactions[Math.floor(Math.random() * transactions.length)];
      const txnId = randomTx.txn_id;
      
      const lineageResp = http.get(`${QUERY_API}/api/query/transactions/lineage/${txnId}`);
      
      check(lineageResp, {
        "lineage query is 200": (r) => r.status === 200,
        "lineage has transaction": (r) => r.json("transaction") !== undefined,
        "lineage query fast": (r) => r.timings.duration < 500,
      });
      
      // Aggregate查询
      const aggregateResp = http.get(`${QUERY_API}/api/query/transactions/lineage/${txnId}/aggregate`);
      
      check(aggregateResp, {
        "aggregate query is 200": (r) => r.status === 200,
        "aggregate has bus_events": (r) => Array.isArray(r.json("bus_events")),
      });
    }
  }
}
