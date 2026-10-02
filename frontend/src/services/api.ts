import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; full_name: string; phone?: string; password: string }) =>
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  updateMe: (data: Partial<{ email: string; full_name: string; phone: string }>) =>
    api.patch('/auth/me', data),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/me/change-password', { current_password, new_password }),
  // Admin
  listUsers: (skip = 0, limit = 100) => api.get('/auth/users', { params: { skip, limit } }),
  getUser: (id: number) => api.get(`/auth/users/${id}`),
  updateUser: (id: number, data: Partial<{ email: string; full_name: string; phone: string; is_active: boolean; is_verified: boolean }>) =>
    api.patch(`/auth/users/${id}`, data),
  deleteUser: (id: number) => api.delete(`/auth/users/${id}`),
};

// Vehicles API
export const vehiclesApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get('/vehicles', { params }),
  get: (id: number) => api.get(`/vehicles/${id}`),
  create: (data: {
    make: string;
    model: string;
    year: number;
    vin?: string;
    license_plate: string;
    color?: string;
    mileage?: number;
    engine_type?: string;
    transmission?: string;
    fuel_type?: string;
    notes?: string;
  }) => api.post('/vehicles', data),
  update: (id: number, data: Partial<{
    make: string;
    model: string;
    year: number;
    vin?: string;
    license_plate: string;
    color?: string;
    mileage?: number;
    engine_type?: string;
    transmission?: string;
    fuel_type?: string;
    notes?: string;
  }>) => api.patch(`/vehicles/${id}`, data),
  delete: (id: number) => api.delete(`/vehicles/${id}`),
};

// Service Types API
export const serviceTypesApi = {
  list: (params?: { category?: string; is_active?: boolean; skip?: number; limit?: number }) =>
    api.get('/service-types', { params }),
  getCategories: () => api.get('/service-types/categories'),
  get: (id: number) => api.get(`/service-types/${id}`),
  create: (data: {
    name: string;
    description?: string;
    category: string;
    base_price: number;
    estimated_duration_minutes: number;
    is_active?: boolean;
  }) => api.post('/service-types', data),
  update: (id: number, data: Partial<{
    name: string;
    description?: string;
    category: string;
    base_price: number;
    estimated_duration_minutes: number;
    is_active?: boolean;
  }>) => api.patch(`/service-types/${id}`, data),
  delete: (id: number) => api.delete(`/service-types/${id}`),
};

// Orders API
export const ordersApi = {
  list: (params?: {
    status?: string;
    customer_id?: number;
    mechanic_id?: number;
    vehicle_id?: number;
    skip?: number;
    limit?: number;
  }) => api.get('/orders', { params }),
  get: (id: number) => api.get(`/orders/${id}`),
  create: (data: {
    vehicle_id: number;
    description?: string;
    customer_notes?: string;
    items: Array<{
      service_type_id?: number;
      part_id?: number;
      quantity: number;
      unit_price: number;
      description?: string;
      is_labor: boolean;
    }>;
  }) => api.post('/orders', data),
  update: (id: number, data: Partial<{
    vehicle_id: number;
    mechanic_id: number;
    status: string;
    description?: string;
    mechanic_notes?: string;
    customer_notes?: string;
    discount: number;
    tax: number;
  }>) => api.patch(`/orders/${id}`, data),
  updateStatus: (id: number, status: string, mechanic_notes?: string) =>
    api.patch(`/orders/${id}/status`, { status, mechanic_notes }),
  delete: (id: number) => api.delete(`/orders/${id}`),
};

// Appointments API
export const appointmentsApi = {
  list: (params?: {
    status?: string;
    customer_id?: number;
    mechanic_id?: number;
    vehicle_id?: number;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/appointments', { params }),
  getCalendar: (start_date: string, end_date: string, mechanic_id?: number) =>
    api.get('/appointments/calendar', { params: { start_date, end_date, mechanic_id } }),
  get: (id: number) => api.get(`/appointments/${id}`),
  create: (data: {
    vehicle_id: number;
    scheduled_at: string;
    estimated_duration_minutes: number;
    notes?: string;
    order_id?: number;
    mechanic_id?: number;
  }) => api.post('/appointments', data),
  update: (id: number, data: Partial<{
    vehicle_id: number;
    order_id: number;
    mechanic_id: number;
    status: string;
    scheduled_at: string;
    estimated_duration_minutes: number;
    notes?: string;
    cancellation_reason?: string;
  }>) => api.patch(`/appointments/${id}`, data),
  updateStatus: (id: number, status: string, cancellation_reason?: string) =>
    api.patch(`/appointments/${id}/status`, { status, cancellation_reason }),
  delete: (id: number) => api.delete(`/appointments/${id}`),
};

// Invoices API
export const invoicesApi = {
  list: (params?: {
    status?: string;
    customer_id?: number;
    start_date?: string;
    end_date?: string;
    overdue_only?: boolean;
    skip?: number;
    limit?: number;
  }) => api.get('/invoices', { params }),
  get: (id: number) => api.get(`/invoices/${id}`),
  create: (data: {
    order_id: number;
    due_date?: string;
    notes?: string;
    discount?: number;
    tax?: number;
  }) => api.post('/invoices', data),
  update: (id: number, data: Partial<{
    due_date?: string;
    notes?: string;
    discount?: number;
    tax?: number;
    status?: string;
  }>) => api.patch(`/invoices/${id}`, data),
  send: (id: number) => api.post(`/invoices/${id}/send`),
  addPayment: (invoice_id: number, data: {
    amount: number;
    method: string;
    notes?: string;
  }) => api.post(`/invoices/${invoice_id}/payments`, data),
  listPayments: (invoice_id: number) => api.get(`/invoices/${invoice_id}/payments`),
  delete: (id: number) => api.delete(`/invoices/${id}`),
};

// Parts API
export const partsApi = {
  list: (params?: {
    category?: string;
    service_type_id?: number;
    is_active?: boolean;
    low_stock_only?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/parts', { params }),
  getCategories: () => api.get('/parts/categories'),
  getLowStock: () => api.get('/parts/low-stock'),
  get: (id: number) => api.get(`/parts/${id}`),
  getMovements: (id: number, params?: { skip?: number; limit?: number }) =>
    api.get(`/parts/${id}/movements`, { params }),
  create: (data: {
    name: string;
    part_number: string;
    manufacturer?: string;
    category: string;
    description?: string;
    purchase_price: number;
    sale_price: number;
    quantity_in_stock?: number;
    min_stock_level?: number;
    unit?: string;
    location?: string;
    is_active?: boolean;
    service_type_id?: number;
  }) => api.post('/parts', data),
  update: (id: number, data: Partial<{
    name: string;
    part_number: string;
    manufacturer?: string;
    category: string;
    description?: string;
    purchase_price: number;
    sale_price: number;
    quantity_in_stock?: number;
    min_stock_level?: number;
    unit?: string;
    location?: string;
    is_active?: boolean;
    service_type_id?: number;
  }>) => api.patch(`/parts/${id}`, data),
  addStockMovement: (part_id: number, data: {
    movement_type: string;
    quantity: number;
    reference_type?: string;
    reference_id?: number;
    notes?: string;
  }) => api.post(`/parts/${part_id}/stock`, data),
  delete: (id: number) => api.delete(`/parts/${id}`),
};

export default api;