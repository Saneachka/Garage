import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { vehiclesApi } from '../../services/api';
import { Vehicle } from '../../types';
import { formatDate, getStatusBadgeClass } from '../../utils/helpers';
import { Car, Plus, Search, Filter, Edit, Trash2, Eye } from 'lucide-react';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { cn } from '../../utils/helpers';

export function VehiclesPage() {
  const navigate = useNavigate();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const res = await vehiclesApi.list({ limit: 100 });
      setVehicles(res.data);
    } catch (error) {
      toast.error('Failed to load vehicles');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this vehicle?')) return;
    try {
      await vehiclesApi.delete(id);
      toast.success('Vehicle deleted');
      fetchVehicles();
    } catch (error) {
      toast.error('Failed to delete vehicle');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" /></div>;
  }

  const filteredVehicles = vehicles.filter(v =>
    v.make.toLowerCase().includes(search.toLowerCase()) ||
    v.model.toLowerCase().includes(search.toLowerCase()) ||
    v.license_plate.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">My Vehicles</h1>
          <p className="text-secondary-600">Manage your vehicles and view service history</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Vehicle
        </button>
      </div>

      {/* Search */}
      <div className="card p-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
          <input
            type="text"
            placeholder="Search vehicles..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Vehicles List */}
      <div className="card">
        {filteredVehicles.length === 0 ? (
          <div className="p-12 text-center">
            <Car className="h-16 w-16 mx-auto text-secondary-300 mb-4" />
            <h3 className="text-lg font-medium text-secondary-900 mb-2">No vehicles yet</h3>
            <p className="text-secondary-500 mb-6">Add your first vehicle to start tracking services</p>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              <Plus className="h-4 w-4 mr-2" />
              Add Vehicle
            </button>
          </div>
        ) : (
          <div className="divide-y divide-secondary-200">
            {filteredVehicles.map((vehicle) => (
              <div key={vehicle.id} className="p-4 hover:bg-secondary-50 flex items-center justify-between">
                <Link to={`/vehicles/${vehicle.id}`} className="flex-1 flex items-center gap-4">
                  <div className="p-3 bg-primary-100 rounded-xl">
                    <Car className="h-6 w-6 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-secondary-900">
                      {vehicle.year} {vehicle.make} {vehicle.model}
                    </p>
                    <p className="text-sm text-secondary-500">
                      {vehicle.license_plate} • {vehicle.color || 'No color'} • {vehicle.mileage?.toLocaleString() || 'Unknown'} mi
                    </p>
                  </div>
                </Link>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/vehicles/${vehicle.id}`}
                    className="p-2 text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 rounded-lg"
                    title="View details"
                  >
                    <Eye className="h-5 w-5" />
                  </Link>
                  <Link
                    to={`/vehicles/${vehicle.id}`}
                    className="p-2 text-secondary-500 hover:text-secondary-700 hover:bg-secondary-100 rounded-lg"
                    title="Edit"
                  >
                    <Edit className="h-5 w-5" />
                  </Link>
                  <button
                    onClick={() => handleDelete(vehicle.id)}
                    className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg"
                    title="Delete"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showCreate && (
        <VehicleFormModal
          onClose={() => setShowCreate(false)}
          onSuccess={() => { setShowCreate(false); fetchVehicles(); }}
        />
      )}
    </div>
  );
}

// Modal Component
function VehicleFormModal({ onClose, onSuccess, vehicle }: { onClose: () => void; onSuccess: () => void; vehicle?: Vehicle }) {
  const [loading, setLoading] = useState(false);
  const isEdit = !!vehicle;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<{
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
  }>({
    defaultValues: vehicle || {
      make: '',
      model: '',
      year: new Date().getFullYear(),
      license_plate: '',
    },
  });

  useEffect(() => {
    if (vehicle) {
      Object.entries(vehicle).forEach(([key, value]) => {
        if (key in { make: 1, model: 1, year: 1, vin: 1, license_plate: 1, color: 1, mileage: 1, engine_type: 1, transmission: 1, fuel_type: 1, notes: 1 }) {
          setValue(key as any, value as any);
        }
      });
    }
  }, [vehicle, setValue]);

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      if (isEdit && vehicle) {
        await vehiclesApi.update(vehicle.id, data);
        toast.success('Vehicle updated');
      } else {
        await vehiclesApi.create(data);
        toast.success('Vehicle added');
      }
      onSuccess();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save vehicle');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-secondary-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{isEdit ? 'Edit Vehicle' : 'Add Vehicle'}</h2>
          <button onClick={onClose} className="p-1 text-secondary-500 hover:text-secondary-700">×</button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="p-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Make *</label>
              <input {...register('make', { required: true })} className="input" />
              {errors.make && <p className="text-sm text-red-600 mt-1">Required</p>}
            </div>
            <div>
              <label className="label">Model *</label>
              <input {...register('model', { required: true })} className="input" />
              {errors.model && <p className="text-sm text-red-600 mt-1">Required</p>}
            </div>
            <div>
              <label className="label">Year *</label>
              <input type="number" {...register('year', { required: true, min: 1900, max: new Date().getFullYear() + 1 })} className="input" />
            </div>
            <div>
              <label className="label">License Plate *</label>
              <input {...register('license_plate', { required: true })} className="input" placeholder="ABC-123" />
              {errors.license_plate && <p className="text-sm text-red-600 mt-1">Required</p>}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">VIN</label>
              <input {...register('vin')} className="input" placeholder="1HGBH41JXMN109186" maxLength={17} />
            </div>
            <div>
              <label className="label">Color</label>
              <input {...register('color')} className="input" placeholder="Blue" />
            </div>
            <div>
              <label className="label">Mileage</label>
              <input type="number" {...register('mileage', { min: 0 })} className="input" placeholder="0" />
            </div>
            <div>
              <label className="label">Fuel Type</label>
              <select {...register('fuel_type')} className="input">
                <option value="">Select</option>
                <option value="gasoline">Gasoline</option>
                <option value="diesel">Diesel</option>
                <option value="electric">Electric</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>
          </div>
          <div>
            <label className="label">Engine Type</label>
            <input {...register('engine_type')} className="input" placeholder="2.0L Turbo" />
          </div>
          <div>
            <label className="label">Transmission</label>
            <select {...register('transmission')} className="input">
              <option value="">Select</option>
              <option value="automatic">Automatic</option>
              <option value="manual">Manual</option>
              <option value="cvt">CVT</option>
            </select>
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea {...register('notes')} className="input" rows={3} placeholder="Additional notes..." />
          </div>
          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1" disabled={loading}>Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? 'Saving...' : (isEdit ? 'Update' : 'Add Vehicle')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}