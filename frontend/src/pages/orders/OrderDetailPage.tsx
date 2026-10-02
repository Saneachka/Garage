import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ordersApi, vehiclesApi, serviceTypesApi, partsApi, appointmentsApi } from '../../services/api';
import { Order, OrderStatus, OrderItem, Vehicle, ServiceType, Part } from '../../types';
import { formatDate, formatDateTime, formatCurrency, getStatusBadgeClass } from '../../utils/helpers';
import { FileText, Clock, AlertCircle, CheckCircle, XCircle, TrendingUp, Plus, Edit, Trash2, ArrowLeft, DollarSign, Wrench, Package, Calendar } from 'lucide-react';
import { cn } from '../../utils/helpers';
import toast from 'react-hot-toast';

const statusOptions: { value: OrderStatus; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'waiting_parts', label: 'Waiting Parts' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'invoiced', label: 'Invoiced' },
];

export function OrderDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'items' | 'info' | 'appointments' | 'invoices'>('items');
  const isNew = id === 'create';

  useEffect(() => {
    if (!isNew) {
      fetchOrder();
    } else {
      setLoading(false);
    }
  }, [id]);

  const fetchOrder = async () => {
    if (!id) return;
    try {
      const res = await ordersApi.get(Number(id));
      setOrder(res.data);
    } catch (error) {
      toast.error('Failed to load order');
      navigate('/orders');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: OrderStatus) => {
    if (!order) return;
    setSaving(true);
    try {
      await ordersApi.updateStatus(order.id, newStatus);
      toast.success(`Order status updated to ${newStatus.replace('_', ' ')}`);
      fetchOrder();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" /></div>;
  }

  if (!isNew && !order) {
    return <div className="text-center py-12">Order not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-secondary-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-secondary-900">
            {isNew ? 'Create New Order' : order?.order_number}
          </h1>
          {!isNew && <p className="text-secondary-600">{order?.vehicle?.year} {order?.vehicle?.make} {order?.vehicle?.model} • {order?.vehicle?.license_plate}</p>}
        </div>
        {!isNew && order && (
          <div className="flex items-center gap-2">
            <span className={cn('badge', getStatusBadgeClass(order.status))}>
              {order.status.replace('_', ' ')}
            </span>
            <select
              value={order.status}
              onChange={(e) => handleStatusChange(e.target.value as OrderStatus)}
              disabled={saving}
              className="input min-w-[160px] py-1.5 text-sm"
            >
              {statusOptions.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {!isNew && order && (
        <>
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Labor</p>
              <p className="text-2xl font-bold text-secondary-900">{formatCurrency(order.labor_cost)}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Parts</p>
              <p className="text-2xl font-bold text-secondary-900">{formatCurrency(order.parts_cost)}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Discount</p>
              <p className="text-2xl font-bold text-secondary-900">-{formatCurrency(order.discount)}</p>
            </div>
            <div className="card p-4 border-l-4 border-primary-500">
              <p className="text-sm text-secondary-600">Total</p>
              <p className="text-2xl font-bold text-secondary-900">{formatCurrency(order.total_price)}</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="card">
            <div className="border-b border-secondary-200">
              <nav className="flex gap-4 p-4" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('items')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'items' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Items ({order.items?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab('info')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'info' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Info
                </button>
                <button
                  onClick={() => setActiveTab('appointments')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'appointments' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Appointments
                </button>
                <button
                  onClick={() => setActiveTab('invoices')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'invoices' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Invoices
                </button>
              </nav>
            </div>

            <div className="p-4">
              {activeTab === 'items' && (
                <div className="space-y-3">
                  {order.items?.length === 0 ? (
                    <p className="text-center text-secondary-500 py-8">No items added yet</p>
                  ) : (
                    order.items?.map((item) => (
                      <div key={item.id} className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg">
                        <div className="flex items-center gap-4">
                          <div className={cn('p-2 rounded-lg', item.is_labor ? 'bg-blue-100' : 'bg-green-100')}>
                            {item.is_labor ? <Wrench className="h-5 w-5 text-blue-600" /> : <Package className="h-5 w-5 text-green-600" />}
                          </div>
                          <div>
                            <p className="font-medium">{item.service_type?.name || item.part?.name || 'Custom Item'}</p>
                            <p className="text-sm text-secondary-500">{item.description || ''}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatCurrency(item.total_price)}</p>
                          <p className="text-sm text-secondary-500">Qty: {item.quantity} × {formatCurrency(item.unit_price)}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'info' && (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-secondary-600">Customer</p>
                      <p className="font-medium">{order.customer?.full_name}</p>
                      <p className="text-sm text-secondary-500">{order.customer?.email}</p>
                      <p className="text-sm text-secondary-500">{order.customer?.phone || 'No phone'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-secondary-600">Vehicle</p>
                      <p className="font-medium">{order.vehicle?.year} {order.vehicle?.make} {order.vehicle?.model}</p>
                      <p className="text-sm text-secondary-500">{order.vehicle?.license_plate} • {order.vehicle?.color}</p>
                      <p className="text-sm text-secondary-500">{order.vehicle?.mileage?.toLocaleString() || 'Unknown'} mi • VIN: {order.vehicle?.vin || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-secondary-600">Mechanic</p>
                      <p className="font-medium">{order.mechanic?.full_name || 'Unassigned'}</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-secondary-600">Timeline</p>
                      <div className="space-y-2 text-sm">
                        <p><span className="font-medium">Created:</span> {formatDateTime(order.created_at)}</p>
                        {order.started_at && <p><span className="font-medium">Started:</span> {formatDateTime(order.started_at)}</p>}
                        {order.completed_at && <p><span className="font-medium">Completed:</span> {formatDateTime(order.completed_at)}</p>}
                      </div>
                    </div>
                    {order.description && (
                      <div>
                        <p className="text-sm text-secondary-600">Description</p>
                        <p className="whitespace-pre-wrap">{order.description}</p>
                      </div>
                    )}
                    {order.mechanic_notes && (
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <p className="text-sm text-secondary-600">Mechanic Notes</p>
                        <p className="whitespace-pre-wrap">{order.mechanic_notes}</p>
                      </div>
                    )}
                    {order.customer_notes && (
                      <div className="bg-green-50 p-4 rounded-lg">
                        <p className="text-sm text-secondary-600">Customer Notes</p>
                        <p className="whitespace-pre-wrap">{order.customer_notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'appointments' && (
                <div className="space-y-3">
                  <p className="text-center text-secondary-500 py-4">Appointments linked to this order will appear here</p>
                </div>
              )}

              {activeTab === 'invoices' && (
                <div className="space-y-3">
                  <p className="text-center text-secondary-500 py-4">Invoices for this order will appear here</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {isNew && (
        <div className="card p-6">
          <p className="text-center text-secondary-500">Use the Orders page to create a new order</p>
        </div>
      )}
    </div>
  );
}