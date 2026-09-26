import { check, sleep } from 'k6';
import {
  createTravelPlan,
  getTravelPlan,
  updateTravelPlan,
} from '../utils/api-client.js';
import { generateTravelPlan, generateLocation } from '../utils/data-generator.js';

export const options = {
  stages: [
    { duration: '10s', target: 30 }, // Швидкий вихід на 30 користувачів
    { duration: '40s', target: 30 }, // 40 секунд активної конкурентної роботи
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<3000'],
  },
};

export default function () {
  // Створюємо план
  const planData = generateTravelPlan();
  const created = createTravelPlan(planData);

  if (created && created.id) {
    // Читаємо план
    getTravelPlan(created.id);

    // Конкурентне оновлення того самого запису
    const updateData = {
      title: 'Updated under isolation test',
      description: 'Concurrency stress testing',
      budget: 9999,
      version: created.version || 1,
    };
    updateTravelPlan(created.id, updateData);
  }

  sleep(0.1);
}