import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { DEFAULT_THRESHOLDS } from '../config/endpoints.js';
import {
  createTravelPlan,
  getTravelPlan,
  listTravelPlans,
  deleteTravelPlan,
} from '../utils/api-client.js';
import { generateTravelPlan } from '../utils/data-generator.js';

// Кастомні метрики
const errorRate = new Rate('api_stress_errors');

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Нормальне навантаження (50 VUs)
    { duration: '1m',  target: 100 },  // Підвищене навантаження (100 VUs)
    { duration: '1m',  target: 200 },  // Початок стресу (200 VUs)
    { duration: '1m',  target: 300 },  // Критичний стрес / Breaking point (300 VUs)
    { duration: '1m',  target: 50 },   // Спад для перевірки відновлення системи (Recovery)
    { duration: '30s', target: 0 },    // Зупинка
  ],
  thresholds: {
    // Для стрес-тесту ми свідомо очікуємо деградацію, тому робимо м'які пороги:
    'http_req_duration': ['p(95)<3000'],
    'http_req_failed': ['rate<0.25'],
  },
};

export default function () {
  const rand = Math.random();

  // 1. Читання списку (60% запитів)
  if (rand < 0.60) {
    const res = listTravelPlans();
    check(res, {
      'stress read successful': (r) => Array.isArray(r),
    });
  } 
  // 2. Створення та читання плану (40% запитів)
  else {
    const planData = generateTravelPlan();
    const created = createTravelPlan(planData);
    
    if (created && created.id) {
      getTravelPlan(created.id);
      
      // Іноді видаляємо, щоб не роздувати базу
      if (Math.random() < 0.5) {
        deleteTravelPlan(created.id);
      }
    } else {
      errorRate.add(1);
    }
  }

  sleep(0.2); // Мінімальна пауза для створення високого тиску на процесор і пул БД
}