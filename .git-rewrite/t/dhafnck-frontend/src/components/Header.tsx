import React, { useContext, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { User, LogOut, ChevronDown, Settings, Home, Key } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

export const Header: React.FC = () => {
  const authContext = useContext(AuthContext);
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  if (!authContext) {
    return null;
  }

  const { user, logout } = authContext;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <header className="theme-nav px-4 py-3 shadow-sm transition-theme">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/dashboard" className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-base-primary">DhafnckMCP</h1>
          </Link>
          <span className="text-sm text-base-secondary">Multi-Project AI Orchestration Platform</span>
        </div>
        
        {user ? (
          <div className="flex items-center space-x-4">
            {/* Navigation Links */}
            <nav className="hidden md:flex items-center space-x-4">
              <Link 
                to="/dashboard" 
                className="theme-nav-item transition-colors"
              >
                <Home className="h-5 w-5" />
              </Link>
              <Link 
                to="/tokens" 
                className="theme-nav-item transition-colors"
              >
                <Key className="h-5 w-5" />
              </Link>
              <Link 
                to="/profile" 
                className="theme-nav-item transition-colors"
              >
                <Settings className="h-5 w-5" />
              </Link>
            </nav>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User Dropdown */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-background-hover transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-white text-sm font-semibold">
                  {getInitials(user.username)}
                </div>
                <span className="hidden sm:block text-sm font-medium text-base-primary">
                  {user.username}
                </span>
                <ChevronDown className="h-4 w-4 text-base-secondary" />
              </button>

              {/* Dropdown Menu */}
              {dropdownOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-10" 
                    onClick={() => setDropdownOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-surface rounded-lg shadow-lg border border-surface-border z-20">
                    <div className="p-3 border-b border-surface-border">
                      <p className="text-sm font-medium text-base-primary">
                        {user.username}
                      </p>
                      <p className="text-xs text-base-tertiary mt-1">
                        {user.email}
                      </p>
                    </div>
                    
                    <div className="p-2">
                      <Link
                        to="/profile"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center space-x-2 px-3 py-2 text-sm text-base-primary hover:bg-background-hover rounded-md transition-colors"
                      >
                        <User className="h-4 w-4" />
                        <span>Profile</span>
                      </Link>
                      
                      <Link
                        to="/tokens"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center space-x-2 px-3 py-2 text-sm text-base-primary hover:bg-background-hover rounded-md transition-colors"
                      >
                        <Key className="h-4 w-4" />
                        <span>API Tokens</span>
                      </Link>
                      
                      <Link
                        to="/dashboard"
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors md:hidden"
                      >
                        <Home className="h-4 w-4" />
                        <span>Dashboard</span>
                      </Link>
                      
                      <button
                        onClick={handleLogout}
                        className="flex items-center space-x-2 px-3 py-2 text-sm text-error hover:bg-error-light rounded-md transition-colors w-full text-left"
                      >
                        <LogOut className="h-4 w-4" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        ) : (
          /* Show theme toggle for non-authenticated users */
          <ThemeToggle />
        )}
      </div>
    </header>
  );
};