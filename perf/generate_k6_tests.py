"""
性能测试脚本 - K6 负载测试
=========================

测试场景:
1. Smoke Test - 冒烟测试 (基础功能)
2. Load Test - 负载测试 (正常负载)
3. Stress Test - 压力测试 (极限负载)
4. Soak Test - 浸泡测试 (长时间运行)

运行方式:
    docker run --rm -v "$PWD/perf:/perf" grafana/k6 run /perf/smoke_test.js
"""

# 配置文件
K6_CONFIG = {
    "base_url": "http://host.docker.internal:18080",
    "query_api": "http://host.docker.internal:5000",
    "command_api": "http://host.docker.internal:8000",
}

# Smoke Test - 冒烟测试
SMOKE_TEST = '''
import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate } from "k6/metrics";

// 自定义指标
const errorRate = new Rate("errors");

export const options = {
  vus: 5,
  duration: "30s",
  thresholds: {
    http_req_duration: ["p(95)<800"],
    http_req_failed: ["rate<0.01"],
    errors: ["rate<0.01"],
  },
};

const BASE_URL = "http://host.docker.internal:18080";
const QUERY_API = "http://host.docker.internal:5000";
const COMMAND_API = "http://host.docker.internal:8000";

export default function () {
  group("Health Checks", () => {
    // Gateway Health
    const gatewayHealth = http.get(`${BASE_URL}/api/health`);
    const gatewayCheck = check(gatewayHealth, {
      "gateway health is 200": (r) => r.status === 200,
      "gateway response time < 500ms": (r) => r.timings.duration < 500,
    });
    errorRate.add(!gatewayCheck);

    // Query API Health
    const queryHealth = http.get(`${QUERY_API}/api/health`);
    const queryCheck = check(queryHealth, {
      "query api health is 200": (r) => r.status === 200,
    });
    errorRate.add(!queryCheck);

    // Command API Health
    const commandHealth = http.get(`${COMMAND_API}/health`);
    const commandCheck = check(commandHealth, {
      "command api health is 200": (r) => r.status === 200,
    });
    errorRate.add(!commandCheck);
  });

  group("Query Operations", () => {
    // List Object Types
    const objectTypes = http.get(`${QUERY_API}/api/query/object-types`);
    check(objectTypes, {
      "list object types is 200": (r) => r.status === 200,
      "object types response is array": (r) => Array.isArray(r.json()),
    });

    // List Events
    const events = http.get(`${QUERY_API}/api/query/events`);
    check(events, {
      "list events is 200": (r) => r.status === 200,
    });

    // Latest Projection
    const projection = http.get(`${QUERY_API}/api/query/projections/latest`);
    check(projection, {
      "latest projection is 200": (r) => r.status === 200,
      "projection has id": (r) => r.json("projection_id") !== undefined,
    });
  });

  group("Authentication", () => {
    const loginPayload = JSON.stringify({
      username: "viewer",
      password: "viewer",
    });
    
    const login = http.post(`${COMMAND_API}/api/auth/token`, loginPayload, {
      headers: { "Content-Type": "application/json" },
    });
    
    const loginCheck = check(login, {
      "login is 200": (r) => r.status === 200,
      "login returns token": (r) => r.json("access_token") !== undefined,
    });
    
    if (loginCheck) {
      const token = login.json("access_token");
      
      // Secure endpoint access
      const secure = http.get(`${QUERY_API}/api/query/transactions/secure`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      check(secure, {
        "secure endpoint is 200": (r) => r.status === 200,
      });
    }
  });

  sleep(1);
}
'''

# Load Test - 正常负载测试
LOAD_TEST = '''
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
'''

# Stress Test - 压力测试
STRESS_TEST = '''
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
'''

# Lineage Query Test - 血缘查询专项测试
LINEAGE_QUERY_TEST = '''
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
'''

# Projection Lag Test - 投影延迟测试
PROJECTION_LAG_TEST = '''
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
'''

# Write all test files
if __name__ == "__main__":
    import os
    
    perf_dir = "perf"
    os.makedirs(perf_dir, exist_ok=True)
    
    tests = {
        "smoke_test.js": SMOKE_TEST,
        "load_test.js": LOAD_TEST,
        "stress_test.js": STRESS_TEST,
        "lineage_query.js": LINEAGE_QUERY_TEST,
        "projection_lag.js": PROJECTION_LAG_TEST,
    }
    
    for filename, content in tests.items():
        filepath = os.path.join(perf_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created: {filepath}")
