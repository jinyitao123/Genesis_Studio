
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "1m", target: 50 },   // 快速增加到50用户
    { duration: "2m", target: 100 },  // 增加到100用户
    { duration: "2m", target: 200 },  // 增加到200用户（预期可能有失败）
    { duration: "2m", target: 100 },  // 降回100用户
    { duration: "1m", target: 0 },    // 逐渐停止
  ],
  thresholds: {
    http_req_duration: ["p(95)<3000"], // 压力测试允许更高延迟
    http_req_failed: ["rate<0.20"],    // 允许最多20%失败
  },
};

const BASE_URL = "http://host.docker.internal:18080";
const QUERY_API = "http://host.docker.internal:5000";
const COMMAND_API = "http://host.docker.internal:8000";

export default function () {
  // 高强度查询
  const resp = http.get(`${QUERY_API}/api/query/transactions`);
  
  const passed = check(resp, {
    "query responds": (r) => r.status === 200,
    "response time < 3s": (r) => r.timings.duration < 3000,
  });
  
  errorRate.add(!passed);
  
  sleep(0.1); // 非常短的间隔，模拟高负载
}
