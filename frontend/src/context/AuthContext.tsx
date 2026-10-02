import { createContext, useContext, useEffect, ReactNode } from 'react';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/api';

interface AuthContextType {
  initializeAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { token, setAuth, logout, setLoading, isAuthenticated } = useAuthStore();

  const initializeAuth = async () => {
    if (!token) return;

    setLoading(true);
    try {
      const response = await authApi.getMe();
      setAuth(response.data, token);
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initializeAuth();
  }, [token]);

  return (
    <AuthContext.Provider value={{ initializeAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}