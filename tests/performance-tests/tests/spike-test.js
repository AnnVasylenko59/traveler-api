import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import {
  createTravelPlan,
  getTravelPlan,
  listTravelPlans,
} from '../utils/api-client.js';
import { generateTravelPlan } from '../utils/data-generator.js';

const failedRequests = new Rate('spike_failed_requests');

export const options = {
  stages: [
    { duration: '30s', target: 5 },    // Нормальний фоновий стан (5 VUs)
    { duration: '10s', target: 250 },  // РІЗКИЙ СПЛЕСК (Spike) до 250 VUs за 10 секунд
    { duration: '1m',  target: 250 },  // Утримання пікового сплеску 1 хвилину
    { duration: '10s', target: 5 },    // Стрімкий спад назад до 5 VUs
    { duration: '30s', target: 5 },    // Період відновлення (Recovery phase)
    { duration: '10s', target: 0 },    // Завершення
  ],
  thresholds: {
    // Під час різкого сплеску допускаємо підвищення часу очікування черги
    'http_req_duration': ['p(95)<3500'],
    'http_req_failed': ['rate<0.15'],
  },
};

export default function () {
  const rand = Math.random();

  // 70% операцій читання списку
  if (rand < 0.70) {
    const plans = listTravelPlans();
    const ok = check(plans, {
      'spike read list ok': (r) => Array.isArray(r),
    });
    if (!ok) failedRequests.add(1);
  } 
  // 30% операцій створення нового плану
  else {
    const data = generateTravelPlan();
    const created = createTravelPlan(data);
    const ok = check(created, {
      'spike plan created ok': (r) => r && r.id !== undefined,
    });
    
    if (ok && created.id) {
      getTravelPlan(created.id);
    } else {
      failedRequests.add(1);
    }
  }

  sleep(0.3); // Коротка пауза між запитами
}