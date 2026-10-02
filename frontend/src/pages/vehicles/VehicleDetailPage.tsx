import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { vehiclesApi, ordersApi, appointmentsApi } from '../../services/api';
import { Vehicle, Order, Appointment } from '../../types';
import { formatDate, formatCurrency, getStatusBadgeClass } from '../../utils/helpers';
import { Car, Calendar, FileText, DollarSign, Wrench, Plus, Edit, ArrowLeft } from 'lucide-react';
import { cn } from '../../utils/helpers';

export function VehicleDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'info' | 'orders' | 'appointments'>('info');
  const isNew = id === 'create';

  useEffect(() => {
    if (!isNew) {
      fetchData();
    } else {
      setLoading(false);
    }
  }, [id]);

  const fetchData = async () => {
    if (!id) return;
    try {
      const [vehicleRes, ordersRes, appointmentsRes] = await Promise.all([
        vehiclesApi.get(Number(id)),
        ordersApi.list({ vehicle_id: Number(id), limit: 20 }),
        appointmentsApi.list({ vehicle_id: Number(id), limit: 20 }),
      ]);
      setVehicle(vehicleRes.data);
      setOrders(ordersRes.data);
      setAppointments(appointmentsRes.data);
    } catch (error) {
      console.error('Failed to load vehicle:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" /></div>;
  }

  if (!isNew && !vehicle) {
    return <div className="text-center py-12">Vehicle not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-secondary-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">
            {isNew ? 'Add Vehicle' : `${vehicle?.year} ${vehicle?.make} ${vehicle?.model}`}
          </h1>
          {!isNew && <p className="text-secondary-600">{vehicle?.license_plate}</p>}
        </div>
      </div>

      {!isNew && (
        <>
          {/* Vehicle Info Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <div className="card p-4">
              <p className="text-sm text-secondary-600">VIN</p>
              <p className="font-mono text-secondary-900">{vehicle?.vin || 'N/A'}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Color</p>
              <p className="font-medium text-secondary-900">{vehicle?.color || 'N/A'}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Mileage</p>
              <p className="font-medium text-secondary-900">{vehicle?.mileage?.toLocaleString() || 'N/A'} mi</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-secondary-600">Fuel</p>
              <p className="font-medium text-secondary-900">{vehicle?.fuel_type || 'N/A'}</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="card">
            <div className="border-b border-secondary-200">
              <nav className="flex gap-4 p-4" aria-label="Tabs">
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
                  onClick={() => setActiveTab('orders')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'orders' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Orders ({orders.length})
                </button>
                <button
                  onClick={() => setActiveTab('appointments')}
                  className={cn(
                    'pb-3 font-medium text-sm border-b-2 transition-colors',
                    activeTab === 'appointments' ? 'border-primary-500 text-primary-600' : 'border-transparent text-secondary-500 hover:text-secondary-700'
                  )}
                >
                  Appointments ({appointments.length})
                </button>
              </nav>
            </div>

            <div className="p-4">
              {activeTab === 'info' && vehicle && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm text-secondary-600">Engine</p>
                      <p className="font-medium">{vehicle.engine_type || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-secondary-600">Transmission</p>
                      <p className="font-medium">{vehicle.transmission || 'N/A'}</p>
                    </div>
                  </div>
                  {vehicle.notes && (
                    <div>
                      <p className="text-sm text-secondary-600">Notes</p>
                      <p className="whitespace-pre-wrap">{vehicle.notes}</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'orders' && (
                <div className="space-y-3">
                  {orders.length === 0 ? (
                    <p className="text-center text-secondary-500 py-8">No orders yet</p>
                  ) : (
                    orders.map((order) => (
                      <Link
                        key={order.id}
                        to={`/orders/${order.id}`}
                        className="flex items-center justify-between p-3 hover:bg-secondary-50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-primary-100 rounded-lg">
                            <FileText className="h-5 w-5 text-primary-600" />
                          </div>
                          <div>
                            <p className="font-medium">{order.order_number}</p>
                            <p className="text-sm text-secondary-500">{formatDate(order.created_at)}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatCurrency(order.total_price)}</p>
                          <span className={cn('badge', getStatusBadgeClass(order.status))}>
                            {order.status.replace('_', ' ')}
                          </span>
                        </div>
                      </Link>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'appointments' && (
                <div className="space-y-3">
                  {appointments.length === 0 ? (
                    <p className="text-center text-secondary-500 py-8">No appointments yet</p>
                  ) : (
                    appointments.map((apt) => (
                      <Link
                        key={apt.id}
                        to={`/appointments/${apt.id}`}
                        className="flex items-center justify-between p-3 hover:bg-secondary-50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-green-100 rounded-lg">
                            <Calendar className="h-5 w-5 text-green-600" />
                          </div>
                          <div>
                            <p className="font-medium">{formatDate(apt.scheduled_at)} at {new Date(apt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                            <p className="text-sm text-secondary-500">{apt.notes || 'No notes'}</p>
                          </div>
                        </div>
                        <span className={cn('badge', getStatusBadgeClass(apt.status))}>
                          {apt.status.replace('_', ' ')}
                        </span>
                      </Link>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {isNew && (
        <div className="card p-6">
          <p className="text-center text-secondary-500">Use the Vehicles page to add a new vehicle</p>
        </div>
      )}
    </div>
  );
}