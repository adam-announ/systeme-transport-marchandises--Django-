import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { ThemeProvider } from './context/ThemeContext';

// Components
import Layout from './components/common/Layout';
import ProtectedRoute from './components/common/ProtectedRoute';
import Loading from './components/common/Loading';

// Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';

// Client pages
import ClientDashboard from './pages/client/Dashboard';
import CreateCommande from './pages/client/CreateCommande';
import CommandeList from './pages/client/CommandeList';
import TrackCommande from './pages/client/TrackCommande';

// Transporteur pages
import TransporteurDashboard from './pages/transporteur/Dashboard';
import MissionList from './pages/transporteur/MissionList';
import Navigation from './pages/transporteur/Navigation';

// Admin pages
import AdminDashboard from './pages/admin/Dashboard';
import CommandeManagement from './pages/admin/CommandeManagement';
import TransporteurManagement from './pages/admin/TransporteurManagement';
import ClientManagement from './pages/admin/ClientManagement';
import Settings from './pages/admin/Settings';

// Planificateur pages
import PlanificateurDashboard from './pages/planificateur/Dashboard';
import OptimizationPanel from './pages/planificateur/OptimizationPanel';
import AssignmentPanel from './pages/planificateur/AssignmentPanel';

import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

// Component to redirect to appropriate dashboard based on user role
function DashboardRedirect() {
  const { user } = useAuth();
  
  if (!user) {
    return <Loading />;
  }

  switch (user.role) {
    case 'client':
      return <Navigate to="/client" replace />;
    case 'transporteur':
      return <Navigate to="/transporteur" replace />;
    case 'admin':
      return <Navigate to="/admin" replace />;
    case 'planificateur':
      return <Navigate to="/planificateur" replace />;
    default:
      return <Navigate to="/login" replace />;
  }
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <NotificationProvider>
            <Router>
              <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
                <Routes>
                  {/* Routes publiques */}
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  
                  {/* Routes protégées avec Layout */}
                  <Route 
                    path="/*" 
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <Routes>
                            {/* Client routes */}
                            <Route 
                              path="client" 
                              element={
                                <ProtectedRoute allowedRoles={['client']}>
                                  <ClientDashboard />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="client/commandes/new" 
                              element={
                                <ProtectedRoute allowedRoles={['client']}>
                                  <CreateCommande />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="client/commandes" 
                              element={
                                <ProtectedRoute allowedRoles={['client']}>
                                  <CommandeList />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="client/commandes/:id/track" 
                              element={
                                <ProtectedRoute allowedRoles={['client']}>
                                  <TrackCommande />
                                </ProtectedRoute>
                              } 
                            />

                            {/* Transporteur routes */}
                            <Route 
                              path="transporteur" 
                              element={
                                <ProtectedRoute allowedRoles={['transporteur']}>
                                  <TransporteurDashboard />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="transporteur/missions" 
                              element={
                                <ProtectedRoute allowedRoles={['transporteur']}>
                                  <MissionList />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="transporteur/navigation/:commandeId" 
                              element={
                                <ProtectedRoute allowedRoles={['transporteur']}>
                                  <Navigation />
                                </ProtectedRoute>
                              } 
                            />

                            {/* Admin routes */}
                            <Route 
                              path="admin" 
                              element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                  <AdminDashboard />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="admin/commandes" 
                              element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                  <CommandeManagement />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="admin/transporteurs" 
                              element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                  <TransporteurManagement />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="admin/clients" 
                              element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                  <ClientManagement />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="admin/settings" 
                              element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                  <Settings />
                                </ProtectedRoute>
                              } 
                            />

                            {/* Planificateur routes */}
                            <Route 
                              path="planificateur" 
                              element={
                                <ProtectedRoute allowedRoles={['planificateur']}>
                                  <PlanificateurDashboard />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="planificateur/optimization" 
                              element={
                                <ProtectedRoute allowedRoles={['planificateur']}>
                                  <OptimizationPanel />
                                </ProtectedRoute>
                              } 
                            />
                            <Route 
                              path="planificateur/assignment" 
                              element={
                                <ProtectedRoute allowedRoles={['planificateur']}>
                                  <AssignmentPanel />
                                </ProtectedRoute>
                              } 
                            />

                            {/* Redirect root to appropriate dashboard */}
                            <Route path="/" element={<DashboardRedirect />} />
                            
                            {/* 404 route */}
                            <Route path="*" element={<Navigate to="/" replace />} />
                          </Routes>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </div>
              
              {/* Toast notifications */}
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                  success: {
                    duration: 3000,
                    theme: {
                      primary: 'green',
                      secondary: 'black',
                    },
                  },
                }}
              />
            </Router>
          </NotificationProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;