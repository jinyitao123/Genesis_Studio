
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
