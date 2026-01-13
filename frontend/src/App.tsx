import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { MainLayout } from './components/layout/MainLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Products } from './pages/Products';
import { ProductTypes } from './pages/ProductTypes';
import { Users } from './pages/Users';
import { Partners } from './pages/Partners';
import { Distributors } from './pages/Distributors';
import { Leads } from './pages/Leads';
import { Orders } from './pages/Orders';
import { Contracts } from './pages/Contracts';
import { Settings } from './pages/Settings';
import { PennylaneConnections } from './pages/PennylaneConnections';
import { PennylaneCustomers } from './pages/PennylaneCustomers';
import { PennylaneInvoices } from './pages/PennylaneInvoices';
import { PennylaneQuotes } from './pages/PennylaneQuotes';
import { PennylaneSubscriptions } from './pages/PennylaneSubscriptions';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Toaster } from './components/ui/toaster';
import './lib/i18n';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <MainLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
                <Route path="products" element={<ErrorBoundary><Products /></ErrorBoundary>} />
                <Route path="product-types" element={<ErrorBoundary><ProductTypes /></ErrorBoundary>} />
                <Route path="users" element={<ErrorBoundary><Users /></ErrorBoundary>} />
                <Route path="partners" element={<ErrorBoundary><Partners /></ErrorBoundary>} />
                <Route path="distributors" element={<ErrorBoundary><Distributors /></ErrorBoundary>} />
                <Route path="leads" element={<ErrorBoundary><Leads /></ErrorBoundary>} />
                <Route path="orders" element={<ErrorBoundary><Orders /></ErrorBoundary>} />
                <Route path="contracts" element={<ErrorBoundary><Contracts /></ErrorBoundary>} />
                <Route path="settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
                <Route path="pennylane/connections" element={<ErrorBoundary><PennylaneConnections /></ErrorBoundary>} />
                <Route path="pennylane/customers" element={<ErrorBoundary><PennylaneCustomers /></ErrorBoundary>} />
                <Route path="pennylane/invoices" element={<ErrorBoundary><PennylaneInvoices /></ErrorBoundary>} />
                <Route path="pennylane/quotes" element={<ErrorBoundary><PennylaneQuotes /></ErrorBoundary>} />
                <Route path="pennylane/subscriptions" element={<ErrorBoundary><PennylaneSubscriptions /></ErrorBoundary>} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
