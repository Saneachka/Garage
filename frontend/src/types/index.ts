export type UserRole = 'customer' | 'mechanic' | 'admin' | 'manager';

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  vehicles_count?: number;
  orders_count?: number;
  appointments_count?: number;
}

export interface Vehicle {
  id: number;
  owner_id: number;
  make: string;
  model: string;
  year: number;
  vin: string | null;
  license_plate: string;
  color: string | null;
  mileage: number | null;
  engine_type: string | null;
  transmission: string | null;
  fuel_type: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  orders_count?: number;
  appointments_count?: number;
}

export interface ServiceType {
  id: number;
  name: string;
  description: string | null;
  category: string;
  base_price: number;
  estimated_duration_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  parts_count?: number;
}

export type OrderStatus = 'draft' | 'pending' | 'confirmed' | 'in_progress' | 'waiting_parts' | 'completed' | 'cancelled' | 'invoiced';

export interface OrderItem {
  id: number;
  order_id: number;
  service_type_id: number | null;
  part_id: number | null;
  quantity: number;
  unit_price: number;
  total_price: number;
  description: string | null;
  is_labor: boolean;
  created_at: string;
  service_type?: ServiceType;
  part?: Part;
}

export interface Order {
  id: number;
  order_number: string;
  customer_id: number;
  vehicle_id: number;
  mechanic_id: number | null;
  status: OrderStatus;
  total_price: number;
  labor_cost: number;
  parts_cost: number;
  discount: number;
  tax: number;
  description: string | null;
  mechanic_notes: string | null;
  customer_notes: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  customer?: User;
  mechanic?: User | null;
  vehicle?: Vehicle;
  items?: OrderItem[];
}

export type AppointmentStatus = 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

export interface Appointment {
  id: number;
  customer_id: number;
  vehicle_id: number;
  order_id: number | null;
  mechanic_id: number | null;
  status: AppointmentStatus;
  scheduled_at: string;
  estimated_duration_minutes: number;
  actual_start_at: string | null;
  actual_end_at: string | null;
  notes: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  customer?: User;
  vehicle?: Vehicle;
  order?: Order | null;
  mechanic?: User | null;
}

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'partially_paid' | 'overdue' | 'cancelled' | 'refunded';
export type PaymentMethod = 'cash' | 'card' | 'bank_transfer' | 'mobile_pay' | 'other';
export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'refunded';

export interface Payment {
  id: number;
  invoice_id: number;
  amount: number;
  method: PaymentMethod;
  status: PaymentStatus;
  transaction_id: string | null;
  notes: string | null;
  processed_at: string | null;
  created_at: string;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  order_id: number;
  customer_id: number;
  status: InvoiceStatus;
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  paid_amount: number;
  due_date: string | null;
  issued_at: string;
  paid_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  customer?: User;
  order?: Order;
  payments?: Payment[];
  balance_due: number;
}

export interface Part {
  id: number;
  service_type_id: number | null;
  name: string;
  part_number: string;
  manufacturer: string | null;
  category: string;
  description: string | null;
  purchase_price: number;
  sale_price: number;
  quantity_in_stock: number;
  min_stock_level: number;
  unit: string;
  location: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  service_type?: ServiceType | null;
  is_low_stock: boolean;
}

export type StockMovementType = 'in' | 'out' | 'adjustment' | 'return' | 'transfer';

export interface StockMovement {
  id: number;
  part_id: number;
  movement_type: StockMovementType;
  quantity: number;
  reference_type: string | null;
  reference_id: number | null;
  notes: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
}