import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{endpoint:query_health}": ["p(95)<800"],
    "http_req_duration{endpoint:command_health}": ["p(95)<800"],
    "http_req_duration{endpoint:auth_login}": ["p(95)<1200"],
    "http_req_duration{endpoint:secure_transactions}": ["p(95)<1200"],
  },
};

export default function () {
  const queryHealth = http.get("http://localhost:5000/api/health", {
    tags: { endpoint: "query_health" },
  });
  check(queryHealth, {
    "query api health is 200": (r) => r.status === 200,
  });

  const commandHealth = http.get("http://localhost:8000/health", {
    tags: { endpoint: "command_health" },
  });
  check(commandHealth, {
    "command api health is 200": (r) => r.status === 200,
  });

  const loginPayload = JSON.stringify({ username: "viewer", password: "viewer" });
  const loginResponse = http.post("http://localhost:8000/api/auth/token", loginPayload, {
    headers: { "Content-Type": "application/json" },
    tags: { endpoint: "auth_login" },
  });
  check(loginResponse, {
    "auth login is 200": (r) => r.status === 200,
    "auth token exists": (r) => {
      try {
        return typeof r.json("access_token") === "string" && r.json("access_token").length > 0;
      } catch (error) {
        return false;
      }
    },
  });

  const token = loginResponse.json("access_token");
  if (token) {
    const secureTransactions = http.get("http://localhost:5000/api/query/transactions/secure", {
      headers: { Authorization: `Bearer ${token}` },
      tags: { endpoint: "secure_transactions" },
    });
    check(secureTransactions, {
      "secure transactions is 200": (r) => r.status === 200,
    });
  }

  sleep(1);
}
