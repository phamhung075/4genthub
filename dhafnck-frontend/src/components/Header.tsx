import { Home, Key, Settings } from 'lucide-react';
import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { ThemeToggle } from './ThemeToggle';
import { Brand } from './ui/Brand';
import UserProfileDropdown from './UserProfileDropdown';

export const Header: React.FC = () => {
  const authContext = useContext(AuthContext);

  if (!authContext) {
    return null;
  }

  const { user } = authContext;

  return (
    <header className="theme-nav px-6 py-4 shadow-lg backdrop-blur-xl bg-surface/95 border-b border-surface-border transition-theme relative z-[1000]">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/dashboard" className="flex items-center space-x-3 group">

            <div className="flex flex-col">
              <Brand variant="header" />
              <span className="text-xs text-base-tertiary -mt-1">AI Orchestration Platform</span>
            </div>
          </Link>
        </div>
        
        {user ? (
          <div className="flex items-center space-x-4">
            {/* Modern Navigation Links */}
            <nav className="hidden md:flex items-center space-x-2">
              <Link 
                to="/dashboard" 
                className="flex items-center space-x-2 px-4 py-2 rounded-xl theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
              >
                <Home className="h-5 w-5" />
                <span className="font-medium">Dashboard</span>
              </Link>
              <Link 
                to="/tokens" 
                className="flex items-center space-x-2 px-4 py-2 rounded-xl theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
              >
                <Key className="h-5 w-5" />
                <span className="font-medium">Tokens</span>
              </Link>
              <Link 
                to="/profile" 
                className="flex items-center space-x-2 px-4 py-2 rounded-xl theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
              >
                <Settings className="h-5 w-5" />
                <span className="font-medium">Settings</span>
              </Link>
            </nav>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User Profile Dropdown */}
            <UserProfileDropdown />
          </div>
        ) : (
          /* Show theme toggle for non-authenticated users */
          <ThemeToggle />
        )}
      </div>
    </header>
  );
};