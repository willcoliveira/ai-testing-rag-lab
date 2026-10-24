// S9: the k6 smoke against the perf stub (docs/OBSERVABILITY.md, docs/THRESHOLDS.md). Run by
// scripts/perf_smoke.py (`make perf-smoke`), never by hand against anything but its loopback server.
//
// One virtual user, because /ask runs behind a lock: more users would measure the queue, not the
// service. A warm-up of WARMUP requests is not gated; then COUNT requests, whose durations go to
// the ask_duration trend. Every reply must be 200 with status ok (checks rate 1) and no request
// may fail. The median of ask_duration is gated at T, set by the rule in THRESHOLDS.md (ten
// report-only runs on GitHub's runner, T = 2 x the largest of their medians, rounded up to the next
// 10 ms); p90, p95, the minimum and the maximum are reported, never gated.
// The questions are written here, none from the golden set's test split, and each carries a
// marker that perf_smoke.py then looks for in the collector's file: it must appear nowhere.
import http from 'k6/http';
import { check } from 'k6';
import exec from 'k6/execution';
import { Trend } from 'k6/metrics';

// T in milliseconds, set on 2026-10-24 by the rule from ten report-only runs of the perf job on
// GitHub's runner (pr-fast run 40074154534, attempts 1 to 10; the largest median 15.38 ms, so
// 2 x 15.38 = 30.76 ms, rounded up to the next 10 ms); tests/unit/test_perf_smoke.py holds it equal
// to THRESHOLDS.md's cell, and it changes only in a reviewed pull request with ten new runs
const MEDIAN_THRESHOLD_MS = 40;
const WARMUP = 10;
const COUNT = 100;
const QUESTIONS = [
  'How many characters must a password have? perf-marker-01',
  'When does an account lock after failed sign-ins? perf-marker-02',
  'Must administrators use MFA? perf-marker-03',
  'How long do VPN sessions last before they disconnect? perf-marker-04',
  'Who approves an exception to the password rules? perf-marker-05',
];

const askDuration = new Trend('ask_duration', true);
const thresholds = {
  checks: ['rate==1'],
  http_req_failed: ['rate==0'],
};
if (MEDIAN_THRESHOLD_MS !== null) {
  thresholds.ask_duration = [`med<${MEDIAN_THRESHOLD_MS}`];
}

export const options = {
  scenarios: {
    smoke: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: WARMUP + COUNT,
      maxDuration: '5m',
    },
  },
  thresholds,
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)'],
};

export default function () {
  const iteration = exec.vu.iterationInScenario;
  const warmup = iteration < WARMUP;
  const body = JSON.stringify({
    tenant: 'tenant-a',
    question: QUESTIONS[iteration % QUESTIONS.length],
  });
  const response = http.post(`${__ENV.BASE_URL}/ask`, body, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${__ENV.TOKEN}` },
    tags: { name: 'ask', phase: warmup ? 'warmup' : 'smoke' },
  });
  check(response, {
    'status 200 and answer ok': (r) => r.status === 200 && r.json('status') === 'ok',
  });
  if (!warmup) {
    askDuration.add(response.timings.duration);
  }
}
