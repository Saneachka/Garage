import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getStatusBadgeClass(status: string): string {
  const statusClasses: Record<string, string> = {
    // Order statuses
    draft: 'badge-secondary',
    pending: 'badge-warning',
    confirmed: 'badge-primary',
    in_progress: 'badge-primary',
    waiting_parts: 'badge-warning',
    completed: 'badge-success',
    cancelled: 'badge-danger',
    invoiced: 'badge-success',

    // Appointment statuses
    scheduled: 'badge-primary',
    confirmed: 'badge-primary',
    no_show: 'badge-danger',

    // Invoice statuses
    sent: 'badge-primary',
    paid: 'badge-success',
    partially_paid: 'badge-warning',
    overdue: 'badge-danger',
    refunded: 'badge-secondary',

    // Payment statuses
    completed: 'badge-success',
    failed: 'badge-danger',
    pending: 'badge-warning',

    // Stock movement types
    in: 'badge-success',
    out: 'badge-primary',
    adjustment: 'badge-warning',
    return: 'badge-secondary',
    transfer: 'badge-primary',
  };

  return statusClasses[status] || 'badge-secondary';
}

export function getRoleBadgeClass(role: string): string {
  const roleClasses: Record<string, string> = {
    admin: 'badge-danger',
    manager: 'badge-warning',
    mechanic: 'badge-primary',
    customer: 'badge-secondary',
  };
  return roleClasses[role] || 'badge-secondary';
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}