import React from 'react';
import { Routes, Route } from 'react-router-dom';
import RegistrationSuccess from '../pages/RegistrationSuccess';

/**
 * Add this route to your main App.tsx or routing configuration
 */
export const RegistrationRoutes = () => {
  return (
    <Routes>
      {/* Registration Success Page */}
      <Route path="/registration-success" element={<RegistrationSuccess />} />
      
      {/* Other routes... */}
    </Routes>
  );
};

/**
 * Or add directly to your existing router setup:
 * 
 * import RegistrationSuccess from './pages/RegistrationSuccess';
 * 
 * <Route path="/registration-success" element={<RegistrationSuccess />} />
 */

// Example App.tsx integration:
export const AppRoutesExample = `
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import RegistrationSuccess from './pages/RegistrationSuccess';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/registration-success" element={<RegistrationSuccess />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}
`;