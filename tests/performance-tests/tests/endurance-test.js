import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import {
  createTravelPlan,
  getTravelPlan,
  listTravelPlans,
  deleteTravelPlan,
} from '../utils/api-client.js';
import { generateTravelPlan } from '../utils/data-generator.js';

const failedRequests = new Rate('endurance_failed_requests');

export const options = {
  stages: [
    { duration: '1m',  target: 25 },  // Плавний вихід на робочий режим (25 VUs)
    { duration: '28m', target: 25 },  // Тривале утримання навантаження (Endurance phase)
    { duration: '1m',  target: 0 },   // Плавне завершення
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.02'],
  },
};

export default function () {
  const rand = Math.random();

  // 60% запитів - перегляд списку планів
  if (rand < 0.60) {
    const plans = listTravelPlans();
    const ok = check(plans, {
      'endurance read list ok': (r) => Array.isArray(r),
    });
    if (!ok) failedRequests.add(1);
  } 
  // 40% запитів - створення, перевірка та очищення
  else {
    const planData = generateTravelPlan();
    const created = createTravelPlan(planData);
    const ok = check(created, {
      'endurance plan created ok': (r) => r && r.id !== undefined,
    });

    if (ok && created.id) {
      getTravelPlan(created.id);
      
      // Видаляємо створений план, щоб база не переповнювалася під час 30-хвилинного тесту
      deleteTravelPlan(created.id);
    } else {
      failedRequests.add(1);
    }
  }

  sleep(0.5); // Стабільний ритм реального фонового навантаження
}