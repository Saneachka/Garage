import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ordersApi, appointmentsApi, invoicesApi, vehiclesApi, partsApi } from '../services/api';
import { Order, Appointment, Invoice, Vehicle, Part } from '../types';
import { formatCurrency, getStatusBadgeClass } from '../utils/helpers';
import {
  Car, FileText, Calendar, DollarSign, Package, AlertTriangle,
  TrendingUp, Clock, CheckCircle, XCircle, AlertCircle, Plus
} from 'lucide-react';
import { cn } from '../utils/helpers';

interface DashboardStats {
  totalVehicles: number;
  activeOrders: number;
  upcomingAppointments: number;
  pendingInvoices: number;
  lowStockParts: number;
  recentOrders: Order[];
  upcomingAppointmentsList: Appointment[];
  pendingInvoicesList: Invoice[];
}

export function DashboardPage() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  const fetchDashboardData = async () => {
    if (!user) return;

    try {
      const params = user.role === 'customer' ? { customer_id: user.id } : {};

      const [
        vehiclesRes,
        ordersRes,
        appointmentsRes,
        invoicesRes,
        partsRes,
      ] = await Promise.all([
        vehiclesApi.list({ limit: 1 }),
        ordersApi.list({ ...params, status: 'in_progress', limit: 5 }),
        appointmentsApi.list({
          ...params,
          start_date: new Date().toISOString().split('T')[0],
          limit: 5,
        }),
        invoicesApi.list({ ...params, status: 'sent', limit: 5 }),
        partsApi.getLowStock(),
      ]);

      const recentOrdersRes = await ordersApi.list({ ...params, limit: 5 });

      setStats({
        totalVehicles: vehiclesRes.data.length || 0,
        activeOrders: ordersRes.data.length || 0,
        upcomingAppointments: appointmentsRes.data.length || 0,
        pendingInvoices: invoicesRes.data.length || 0,
        lowStockParts: partsRes.data.length || 0,
        recentOrders: recentOrdersRes.data,
        upcomingAppointmentsList: appointmentsRes.data,
        pendingInvoicesList: invoicesRes.data,
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  const statCards = [
    {
      title: 'My Vehicles',
      value: stats?.totalVehicles || 0,
      icon: Car,
      color: 'text-blue-600 bg-blue-100',
      href: '/vehicles',
    },
    {
      title: 'Active Orders',
      value: stats?.activeOrders || 0,
      icon: FileText,
      color: 'text-yellow-600 bg-yellow-100',
      href: '/orders?status=in_progress',
    },
    {
      title: 'Upcoming Appointments',
      value: stats?.upcomingAppointments || 0,
      icon: Calendar,
      color: 'text-green-600 bg-green-100',
      href: '/appointments',
    },
    {
      title: 'Pending Invoices',
      value: stats?.pendingInvoices || 0,
      icon: DollarSign,
      color: 'text-red-600 bg-red-100',
      href: '/invoices?status=sent',
    },
  ];

  // Add low stock for staff
  if (user && ['admin', 'manager'].includes(user.role)) {
    statCards.push({
      title: 'Low Stock Parts',
      value: stats?.lowStockParts || 0,
      icon: AlertTriangle,
      color: 'text-orange-600 bg-orange-100',
      href: '/parts?low_stock=true',
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">
            Welcome back, {user?.full_name?.split(' ')[0]}!
          </h1>
          <p className="text-secondary-600">Here's what's happening with your vehicles today.</p>
        </div>
        {user && ['admin', 'manager', 'mechanic'].includes(user.role) && (
          <Link to="/orders/create" className="btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            New Order
          </Link>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
        {statCards.map((stat) => (
          <Link
            key={stat.title}
            to={stat.href}
            className="card p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">{stat.title}</p>
                <p className="text-3xl font-bold text-secondary-900 mt-1">{stat.value}</p>
              </div>
              <div className={cn('p-3 rounded-xl', stat.color)}>
                <stat.icon className="h-6 w-6" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* Recent Orders */}
        <div className="card lg:col-span-2">
          <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">Recent Orders</h2>
            <Link to="/orders" className="text-sm text-primary-600 hover:underline">View all</Link>
          </div>
          <div className="divide-y divide-secondary-200">
            {stats?.recentOrders.length === 0 ? (
              <div className="p-8 text-center text-secondary-500">
                <FileText className="h-12 w-12 mx-auto text-secondary-300 mb-2" />
                <p>No orders yet</p>
              </div>
            ) : (
              stats?.recentOrders.map((order) => (
                <Link
                  key={order.id}
                  to={`/orders/${order.id}`}
                  className="p-4 hover:bg-secondary-50 flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-primary-100 rounded-lg">
                      <FileText className="h-5 w-5 text-primary-600" />
                    </div>
                    <div>
                      <p className="font-medium text-secondary-900">{order.order_number}</p>
                      <p className="text-sm text-secondary-500">
                        {order.vehicle?.make} {order.vehicle?.model} ({order.vehicle?.license_plate})
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-secondary-900">{formatCurrency(order.total_price)}</p>
                    <span className={cn('badge', getStatusBadgeClass(order.status))}>
                      {order.status.replace('_', ' ')}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Upcoming Appointments */}
        <div className="card">
          <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">Upcoming Appointments</h2>
            <Link to="/appointments" className="text-sm text-primary-600 hover:underline">View all</Link>
          </div>
          <div className="divide-y divide-secondary-200">
            {stats?.upcomingAppointmentsList.length === 0 ? (
              <div className="p-8 text-center text-secondary-500">
                <Calendar className="h-12 w-12 mx-auto text-secondary-300 mb-2" />
                <p>No upcoming appointments</p>
              </div>
            ) : (
              stats?.upcomingAppointmentsList.map((apt) => (
                <Link
                  key={apt.id}
                  to={`/appointments/${apt.id}`}
                  className="p-4 hover:bg-secondary-50"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <Calendar className="h-5 w-5 text-green-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-secondary-900 truncate">
                        {apt.vehicle?.make} {apt.vehicle?.model}
                      </p>
                      <p className="text-sm text-secondary-500">
                        {new Date(apt.scheduled_at).toLocaleDateString('en-US', {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                    <span className={cn('badge', getStatusBadgeClass(apt.status))}>
                      {apt.status.replace('_', ' ')}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Pending Invoices */}
        <div className="card xl:col-span-2">
          <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900">Pending Invoices</h2>
            <Link to="/invoices" className="text-sm text-primary-600 hover:underline">View all</Link>
          </div>
          <div className="divide-y divide-secondary-200">
            {stats?.pendingInvoicesList.length === 0 ? (
              <div className="p-8 text-center text-secondary-500">
                <DollarSign className="h-12 w-12 mx-auto text-secondary-300 mb-2" />
                <p>No pending invoices</p>
              </div>
            ) : (
              stats?.pendingInvoicesList.map((invoice) => (
                <Link
                  key={invoice.id}
                  to={`/invoices/${invoice.id}`}
                  className="p-4 hover:bg-secondary-50 flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium text-secondary-900">{invoice.invoice_number}</p>
                    <p className="text-sm text-secondary-500">Order: {invoice.order?.order_number}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-secondary-900">{formatCurrency(invoice.balance_due)}</p>
                    <p className="text-sm text-secondary-500">
                      Due: {invoice.due_date ? formatDate(invoice.due_date) : 'N/A'}
                    </p>
                    <span className={cn('badge', getStatusBadgeClass(invoice.status))}>
                      {invoice.status.replace('_', ' ')}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}