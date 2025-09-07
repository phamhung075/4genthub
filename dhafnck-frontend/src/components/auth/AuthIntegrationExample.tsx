import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthWrapper, LoginForm, SignupForm, ProtectedRoute } from './index';

// Example Dashboard component (replace with your actual dashboard)
const Dashboard = () => <div>Dashboard - You are authenticated!</div>;

// Example Admin component (requires admin role)
const AdminPanel = () => <div>Admin Panel - Admin access only!</div>;

// Unauthorized page
const Unauthorized = () => <div>You don't have permission to access this page.</div>;

/**
 * Example integration of authentication components
 * 
 * This shows how to:
 * 1. Wrap your app with AuthWrapper
 * 2. Set up public routes (login, signup)
 * 3. Set up protected routes (dashboard, admin)
 * 4. Handle role-based access control
 */
export const AuthIntegrationExample: React.FC = () => {
  return (
    <AuthWrapper>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginForm />} />
          <Route path="/signup" element={<SignupForm />} />
          <Route path="/unauthorized" element={<Unauthorized />} />
          
          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Admin-only route */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireRoles={['admin']}>
                <AdminPanel />
              </ProtectedRoute>
            }
          />
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthWrapper>
  );
};

/**
 * To integrate into your existing App.tsx:
 * 
 * 1. Import the components:
 *    import { AuthWrapper, LoginForm, SignupForm, ProtectedRoute } from './components/auth';
 * 
 * 2. Wrap your app with AuthWrapper at the highest level
 * 
 * 3. Add routes for login and signup
 * 
 * 4. Wrap protected components with ProtectedRoute
 * 
 * Example App.tsx modification:
 * 
 * function App() {
 *   return (
 *     <AuthWrapper>
 *       <Router>
 *         <Routes>
 *           <Route path="/login" element={<LoginForm />} />
 *           <Route path="/signup" element={<SignupForm />} />
 *           <Route 
 *             path="/*" 
 *             element={
 *               <ProtectedRoute>
 *                 <YourMainApp />
 *               </ProtectedRoute>
 *             } 
 *           />
 *         </Routes>
 *       </Router>
 *     </AuthWrapper>
 *   );
 * }
 */