import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ordersApi, vehiclesApi, serviceTypesApi } from '../../services/api';
import { Order, OrderStatus, Vehicle } from '../../types';
import { formatDate, formatCurrency, getStatusBadgeClass } from '../../utils/helpers';
import { FileText, Plus, Search, Filter, Clock, AlertCircle, CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import { cn } from '../../utils/helpers';
import toast from 'react-hot-toast';

const statusOptions: { value: OrderStatus; label: string; icon: typeof Clock }[] = [
  { value: 'draft', label: 'Draft', icon: FileText },
  { value: 'pending', label: 'Pending', icon: Clock },
  { value: 'confirmed', label: 'Confirmed', icon: CheckCircle },
  { value: 'in_progress', label: 'In Progress', icon: TrendingUp },
  { value: 'waiting_parts', label: 'Waiting Parts', icon: AlertCircle },
  { value: 'completed', label: 'Completed', icon: CheckCircle },
  { value: 'cancelled', label: 'Cancelled', icon: XCircle },
  { value: 'invoiced', label: 'Invoiced', icon: FileText },
];

export function OrdersPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const fetchOrders = async () => {
    try {
      const res = await ordersApi.list({ status: statusFilter || undefined, limit: 50 });
      setOrders(res.data);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const filteredOrders = orders.filter(o =>
    o.order_number.toLowerCase().includes(search.toLowerCase()) ||
    o.vehicle?.make.toLowerCase().includes(search.toLowerCase()) ||
    o.vehicle?.model.toLowerCase().includes(search.toLowerCase()) ||
    o.vehicle?.license_plate.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Orders</h1>
          <p className="text-secondary-600">Manage service orders and track progress</p>
        </div>
        <Link to="/orders/create" className="btn-primary">
          <Plus className="h-4 w-4 mr-2" />
          Create Order
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
            <input
              type="text"
              placeholder="Search orders..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input min-w-[180px]"
          >
            <option value="">All Statuses</option>
            {statusOptions.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="card">
        {loading ? (
          <div className="p-8 text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-16 w-16 mx-auto text-secondary-300 mb-4" />
            <h3 className="text-lg font-medium text-secondary-900 mb-2">No orders found</h3>
            <p className="text-secondary-500 mb-6">Create your first service order</p>
            <Link to="/orders/create" className="btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Create Order
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-secondary-200 bg-secondary-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Order #</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Vehicle</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Mechanic</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-secondary-500 uppercase tracking-wider">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-secondary-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-200">
                {filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-secondary-50">
                    <td className="px-4 py-3">
                      <Link to={`/orders/${order.id}`} className="font-mono text-primary-600 hover:underline">
                        {order.order_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{order.customer?.full_name}</p>
                      <p className="text-sm text-secondary-500">{order.customer?.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{order.vehicle?.year} {order.vehicle?.make} {order.vehicle?.model}</p>
                      <p className="text-sm text-secondary-500">{order.vehicle?.license_plate}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('badge', getStatusBadgeClass(order.status))}>
                        {order.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {order.mechanic ? (
                        <p className="font-medium">{order.mechanic.full_name}</p>
                      ) : (
                        <p className="text-secondary-400">Unassigned</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(order.total_price)}</td>
                    <td className="px-4 py-3 text-sm text-secondary-500">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/orders/${order.id}`} className="text-primary-600 hover:underline text-sm">View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}