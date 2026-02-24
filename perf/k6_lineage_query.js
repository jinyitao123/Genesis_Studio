import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "20s",
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{endpoint:lineage_query}": ["p(95)<1200"],
  },
};

export default function () {
  const response = http.get("http://localhost:5000/api/query/transactions/lineage/txn-1", {
    tags: { endpoint: "lineage_query" },
  });
  check(response, {
    "lineage endpoint available": (r) => r.status === 200 || r.status === 404,
  });
  sleep(1);
}
