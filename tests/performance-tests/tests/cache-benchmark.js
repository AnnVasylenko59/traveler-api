import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 30 },  // Розгін до 30 користувачів
    { duration: '20s', target: 30 }, // 20 секунд інтенсивного читання з кешу
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<10'], // Висока швидкодія завдяки кешу
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export function setup() {
  // Створюємо план, щоб отримати валідний ID для багаторазового читання
  const payload = JSON.stringify({
    title: 'Cache Benchmark Plan',
    description: 'Testing LRU speedup',
    start_date: '2026-10-01',
    end_date: '2026-10-10',
    budget: 1000,
    currency: 'USD',
    is_public: true,
  });

  const res = http.post(`${BASE_URL}/api/travel-plans`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  const data = JSON.parse(res.body);
  return { planId: data.id };
}

export default function (data) {
  // Багаторазове читання того самого плану (демонстрація Cache Hit)
  const res = http.get(`${BASE_URL}/api/travel-plans/${data.planId}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(0.01);
}