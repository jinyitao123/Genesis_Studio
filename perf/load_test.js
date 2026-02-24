
import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const actionDispatchDuration = new Trend("action_dispatch_duration");

export const options = {
  stages: [
    { duration: "2m", target: 10 },   // 缓慢增加到10用户
    { duration: "5m", target: 10 },   // 保持10用户5分钟
    { duration: "2m", target: 20 },   // 增加到20用户
    { duration: "5m", target: 20 },   // 保持20用户5分钟
    { duration: "2m", target: 0 },    // 逐渐减到0
  ],
  thresholds: {
    http_req_duration: ["p(95)<1000"],
    http_req_failed: ["rate<0.05"],
    action_dispatch_duration: ["p(95)<1500"],
  },
};

const BASE_URL = "http://host.docker.internal:18080";
const QUERY_API = "http://host.docker.internal:5000";
const COMMAND_API = "http://host.docker.internal:8000";

export function setup() {
  // 获取token用于后续请求
  const loginResp = http.post(`${COMMAND_API}/api/auth/token`, JSON.stringify({
    username: "designer",
    password: "designer",
  }), {
    headers: { "Content-Type": "application/json" },
  });
  
  return { token: loginResp.json("access_token") };
}

export default function (data) {
  const token = data.token;
  const headers = { Authorization: `Bearer ${token}` };

  group("Read Heavy Operations", () => {
    // 并行查询
    const responses = http.batch([
      ["GET", `${QUERY_API}/api/query/object-types`, null, { headers }],
      ["GET", `${QUERY_API}/api/query/events`, null, { headers }],
      ["GET", `${QUERY_API}/api/query/projections/latest`, null, { headers }],
      ["GET", `${QUERY_API}/api/query/transactions`, null, { headers }],
    ]);
    
    responses.forEach((resp, idx) => {
      const checkName = ["object types", "events", "projection", "transactions"][idx];
      const passed = check(resp, {
        [`${checkName} is 200`]: (r) => r.status === 200,
      });
      errorRate.add(!passed);
    });
  });

  group("Action Dispatch", () => {
    const payload = JSON.stringify({
      action_id: "ACT_LOAD_TEST",
      source_id: `load-test-${__VU}-${__ITER}`,
      target_id: `target-${__VU}`,
      payload: { test: true, iteration: __ITER },
    });
    
    const start = Date.now();
    const resp = http.post(`${COMMAND_API}/api/command/dispatch`, payload, {
      headers: { ...headers, "Content-Type": "application/json" },
    });
    const duration = Date.now() - start;
    
    actionDispatchDuration.add(duration);
    
    const passed = check(resp, {
      "dispatch accepted": (r) => r.status === 200 || r.status === 202,
    });
    errorRate.add(!passed);
  });

  group("Copilot Operations", () => {
    const payload = JSON.stringify({
      intent: "query_status",
      prompt: "查询系统状态",
      context: {},
    });
    
    const resp = http.post(`${COMMAND_API}/api/copilot/route`, payload, {
      headers: { ...headers, "Content-Type": "application/json" },
    });
    
    const passed = check(resp, {
      "copilot route is 200": (r) => r.status === 200,
    });
    errorRate.add(!passed);
  });

  sleep(Math.random() * 2 + 1); // 1-3秒随机间隔
}
