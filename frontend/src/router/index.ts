import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/graph',
    name: 'graph',
    component: () => import('@/views/GraphView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/timeline',
    name: 'timeline',
    component: () => import('@/views/TimelineView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/logic',
    name: 'logic',
    component: () => import('@/views/LogicView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/lineage',
    name: 'lineage',
    component: () => import('@/views/LineageView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/inspector',
    name: 'inspector',
    component: () => import('@/views/InspectorView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/proposals',
    name: 'proposals',
    component: () => import('@/views/ProposalsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/copilot',
    name: 'copilot',
    component: () => import('@/views/CopilotView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/ops',
    name: 'ops',
    component: () => import('@/views/OpsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/geomap',
    name: 'geomap',
    component: () => import('@/views/GeoMapView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard for authentication
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'home', query: { redirect: to.fullPath } });
  } else {
    next();
  }
});

export default router;
