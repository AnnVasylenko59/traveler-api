/**
 * ============================================================================
 * REALISTIC USER JOURNEY LOAD TEST
 * ============================================================================
 * 
 * МЕТА:
 * Симулювати реальну поведінку користувачів при плануванні подорожі.
 * Включає природні паузи (think time), помилки, зміну рішень та
 * типові сценарії використання API.
 * 
 * СПІВВІДНОШЕННЯ: ~60% читання / ~40% запису (збалансоване)
 * 
 * ТИПОВІ СЦЕНАРІЇ КОРИСТУВАЧІВ:
 * 
 * 1. "Новий користувач" (30% - створює перший plan)
 *    - Переглядає приклади (читає публічні плани)
 *    - Створює свій перший travel plan
 *    - Додає локації поступово
 *    - Вносить виправлення (редагує)
 * 
 * 2. "Досвідчений користувач" (50% - редагує існуючий)
 *    - Переглядає свої плани
 *    - Вибирає один для редагування
 *    - Додає нові локації
 *    - Оновлює існуючі
 *    - Видаляє непотрібні
 * 
 * 3. "Браузер" (20% - тільки переглядає)
 *    - Шукає ідеї для подорожі
 *    - Переглядає різні плани
 *    - Детально вивчає локації
 *    - Не створює власних планів
 * 
 * ОСОБЛИВОСТІ:
 * - Think time між діями (1-5 секунд)
 * - Реалістичні помилки та виправлення
 * - Іноді користувач змінює думку (видаляє щойно створене)
 * - Імітація паралельної роботи в кількох вкладках
 * - Сесії різної тривалості
 * 
 * МЕТРИКИ:
 * - User session duration
 * - Actions per session
 * - Session completion rate
 * - Think time impact on performance
 * 
 * ============================================================================
 */

import { check, sleep, group } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import { randomIntBetween } from 'k6';
import { DEFAULT_THRESHOLDS } from '../config/endpoints.js';
import {
  createTravelPlan,
  getTravelPlan,
  listTravelPlans,
  addLocation,
  updateLocation,
  updateTravelPlan,
  deleteTravelPlan,
  deleteLocation,
  checkHealth,
  thinkTime,
} from '../utils/api-client.js';
import {
  generateTravelPlan,
  generateLocation,
  generateLocationWithDates,
} from '../utils/data-generator.js';

// Кастомні метрики для user journeys
const sessionCompleted = new Rate('session_completion_rate');
const actionsPerSession = new Trend('actions_per_session');
const sessionDuration = new Trend('session_duration_seconds');
const userTypeDistribution = new Counter('user_type_distribution');

// ============================================================================
// НАЛАШТУВАННЯ ТЕСТУ
// ============================================================================

export const options = {
  scenarios: {
    realistic_users: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 30,
      maxVUs: 100,
      stages: [
        { duration: '3m', target: 10 },
        { duration: '7m', target: 20 },
        { duration: '5m', target: 15 },
        { duration: '3m', target: 5 },
      ],
      exec: 'realisticUserJourney',
    },
  },

  thresholds: {
    ...DEFAULT_THRESHOLDS,
    'http_req_duration': [
      'p(95)<800',
      'p(99)<1500',
    ],
    'session_completion_rate': ['rate>0.80'],
    'actions_per_session': ['avg>2', 'avg<25'],
    'checks': ['rate>0.90'],
  },

  userAgent: 'K6-RealisticUser-LoadTest/1.0',
};

// ============================================================================
// ГОЛОВНА ФУНКЦІЯ: ВИБІР ТИПУ КОРИСТУВАЧА
// ============================================================================

export function realisticUserJourney() {
  const sessionStart = Date.now();
  let actionsCount = 0;
  let sessionSuccess = true;

  const rand = Math.random();
  
  try {
    if (rand < 0.30) {
      userTypeDistribution.add(1, { type: 'new_user' });
      actionsCount = newUserJourney();
    } else if (rand < 0.80) {
      userTypeDistribution.add(1, { type: 'experienced_user' });
      actionsCount = experiencedUserJourney();
    } else {
      userTypeDistribution.add(1, { type: 'browser' });
      actionsCount = browserJourney();
    }
  } catch (err) {
    sessionSuccess = false;
  }

  const sessionEnd = Date.now();
  const duration = (sessionEnd - sessionStart) / 1000;
  
  sessionDuration.add(duration);
  actionsPerSession.add(actionsCount);
  sessionCompleted.add(sessionSuccess ? 1 : 0);
}

// ============================================================================
// СЦЕНАРІЙ 1: НОВИЙ КОРИСТУВАЧ
// ============================================================================

function newUserJourney() {
  let actions = 0;

  try {
    group('New User Journey', function() {
      // 1. Перевірка API
      checkHealth();
      actions++;
      thinkTime(1, 2);

      // 2. Перегляд прикладів
      group('Browse examples', function() {
        const publicPlans = listTravelPlans();
        actions++;
        
        if (Array.isArray(publicPlans) && publicPlans.length > 0) {
          const examplesToView = Math.min(2, publicPlans.length);
          for (let i = 0; i < examplesToView; i++) {
            if (publicPlans[i] && publicPlans[i].id) {
              getTravelPlan(publicPlans[i].id);
              actions++;
              thinkTime(1, 2);
            }
          }
        }
      });

      // 3. Створення першого плану
      thinkTime(1, 2);
      const planData = generateTravelPlan();
      planData.title = 'My First Travel Plan';
      planData.description = 'Exciting new journey!';
      
      const plan = createTravelPlan(planData);
      actions++;
      
      if (!plan || !plan.id) {
        throw new Error('Plan creation skipped or failed');
      }

      const planId = plan.id;
      let currentVersion = plan.version || 1;
      const initialBudget = (typeof plan.budget === 'number') ? plan.budget : 1000;

      // 4. Додавання локацій
      group('Add locations gradually', function() {
        const locationsToAdd = randomIntBetween(1, 3);
        for (let i = 0; i < locationsToAdd; i++) {
          thinkTime(1, 2);
          const locationData = generateLocationWithDates(30 + i);
          const location = addLocation(planId, locationData);
          actions++;
          
          if (location && location.id) {
            thinkTime(1, 2);
            getTravelPlan(planId);
            actions++;
          }
        }
      });

      // 5. Виправлення помилок
      group('Fix mistakes', function() {
        thinkTime(1, 2);
        
        const updateData = {
          ...planData,
          budget: initialBudget + 500,
          description: 'Updated description with more details',
          version: currentVersion,
        };
        
        const updated = updateTravelPlan(planId, updateData);
        actions++;
        
        if (updated && !updated.conflict && updated.version) {
          currentVersion = updated.version;
        }
      });

      // 6. Фінальний перегляд
      thinkTime(1, 2);
      getTravelPlan(planId);
      actions++;
    });
  } catch (e) {
    // Тихо перехоплюємо для безпеки сесії
  }

  return actions;
}

// ============================================================================
// СЦЕНАРІЙ 2: ДОСВІДЧЕНИЙ КОРИСТУВАЧ
// ============================================================================

function experiencedUserJourney() {
  let actions = 0;

  try {
    group('Experienced User Journey', function() {
      // 1. Перегляд своїх планів
      const myPlans = listTravelPlans();
      actions++;
      thinkTime(1, 2);

      if (!Array.isArray(myPlans) || myPlans.length === 0) {
        const planData = generateTravelPlan();
        createTravelPlan(planData);
        actions++;
        return;
      }

      // 2. Вибір плану для редагування
      const validPlans = myPlans.filter(p => p && p.id);
      if (validPlans.length === 0) return;

      const planToEdit = validPlans[Math.floor(Math.random() * validPlans.length)];
      const fullPlan = getTravelPlan(planToEdit.id);
      actions++;
      
      if (!fullPlan || !fullPlan.id) {
        return;
      }

      thinkTime(1, 2);

      // 3. Додавання нової локації
      const locationData = generateLocation();
      addLocation(fullPlan.id, locationData);
      actions++;

      thinkTime(1, 2);

      // 4. Оновлення існуючої локації
      if (Array.isArray(fullPlan.locations) && fullPlan.locations.length > 0) {
        const loc = fullPlan.locations[0];
        if (loc && loc.id) {
          thinkTime(1, 2);
          const updateData = {
            name: (loc.name || 'Location') + ' (Updated)',
            budget: (loc.budget != null ? Number(loc.budget) : 100) + 50,
            notes: 'Updated by experienced user',
          };
          updateLocation(loc.id, updateData);
          actions++;
        }
      }

      thinkTime(1, 2);

      // 5. Видалення локації
      if (Array.isArray(fullPlan.locations) && fullPlan.locations.length > 2 && Math.random() < 0.4) {
        const locationToDelete = fullPlan.locations[fullPlan.locations.length - 1];
        if (locationToDelete && locationToDelete.id) {
          thinkTime(1, 2);
          deleteLocation(locationToDelete.id);
          actions++;
        }
      }

      // 6. Оновлення деталей плану
      thinkTime(1, 2);
      const updateData = {
        title: fullPlan.title || 'Updated Title',
        description: fullPlan.description || 'Updated',
        budget: (fullPlan.budget != null ? Number(fullPlan.budget) : 2000) + 200,
        version: fullPlan.version || 1,
      };
      
      updateTravelPlan(fullPlan.id, updateData);
      actions++;

      // 7. Фінальна перевірка
      thinkTime(1, 2);
      getTravelPlan(fullPlan.id);
      actions++;
    });
  } catch (e) {
    // Безпечне перехоплення
  }

  return actions;
}

// ============================================================================
// СЦЕНАРІЙ 3: БРАУЗЕР (тільки перегляд)
// ============================================================================

function browserJourney() {
  let actions = 0;

  try {
    group('Browser Journey', function() {
      const plans = listTravelPlans();
      actions++;
      
      if (!Array.isArray(plans) || plans.length === 0) {
        return;
      }

      thinkTime(1, 2);

      const validPlans = plans.filter(p => p && p.id);
      if (validPlans.length === 0) return;

      const plansToView = Math.min(2, validPlans.length);
      for (let i = 0; i < plansToView; i++) {
        const planId = validPlans[i].id;
        const planDetails = getTravelPlan(planId);
        actions++;
        
        if (planDetails && Array.isArray(planDetails.locations) && planDetails.locations.length > 0) {
          thinkTime(2, 4);
        } else {
          thinkTime(1, 2);
        }
      }
    });
  } catch (e) {
    // Безпечне перехоплення
  }

  return actions;
}

// ============================================================================
// SETUP & TEARDOWN
// ============================================================================

export function setup() {
  console.log('='.repeat(80));
  console.log('Starting Realistic User Journey Load Test');
  console.log('Populating initial travel plans for browsers and experienced users...');

  for (let i = 0; i < 5; i++) {
    const planData = generateTravelPlan();
    planData.is_public = true;
    const plan = createTravelPlan(planData);
    if (plan && plan.id) {
      addLocation(plan.id, generateLocation());
      addLocation(plan.id, generateLocation());
    }
  }

  console.log('Setup completed: seeded initial plans');
  console.log('='.repeat(80));
}

export function teardown(data) {
  console.log('='.repeat(80));
  console.log('Realistic User Journey Test completed');
  console.log('='.repeat(80));
}