import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "20s",
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{endpoint:projection_replay}": ["p(95)<1500"],
  },
};

export default function () {
  const login = http.post(
    "http://localhost:8000/api/auth/token",
    JSON.stringify({ username: "designer", password: "designer" }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(login, { "login ok": (r) => r.status === 200 });
  const token = login.json("access_token");
  if (!token) {
    sleep(1);
    return;
  }

  const replay = http.post(
    "http://localhost:8000/api/command/project/replay",
    JSON.stringify({ from_event_id: "evt-1", correlation_id: "corr-k6" }),
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      tags: { endpoint: "projection_replay" },
    }
  );
  check(replay, { "projection replay queued": (r) => r.status === 200 });
  sleep(1);
}
