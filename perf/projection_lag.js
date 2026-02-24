
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const lagTrend = new Trend("projection_lag");

export const options = {
  vus: 1,
  duration: "5m",
};

const QUERY_API = "http://host.docker.internal:5000";

export default function () {
  const resp = http.get(`${QUERY_API}/api/query/projections/lag`);
  
  if (resp.status === 200) {
    const lag = resp.json("lag");
    lagTrend.add(lag);
    
    check(resp, {
      "lag endpoint is 200": (r) => r.status === 200,
      "lag is reasonable": (r) => lag < 100, // 期望lag小于100个事件
    });
  }
  
  sleep(5); // 每5秒检查一次
}
