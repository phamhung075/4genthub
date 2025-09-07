import { ChevronDown, Home, Key, LogOut, Settings, User } from 'lucide-react';
import React, { useContext, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { ThemeToggle } from './ThemeToggle';
import { Brand } from './ui/Brand';

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
    <header className="theme-nav px-6 py-4 shadow-lg backdrop-blur-xl bg-surface/95 border-b border-surface-border transition-theme">
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

            {/* Modern User Dropdown */}
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center space-x-3 px-4 py-2 rounded-2xl hover:bg-primary/10 transition-all duration-200 border border-surface-border hover:border-primary/20"
              >
                <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-sm font-bold shadow-lg">
                  {getInitials(user.username)}
                </div>
                <div className="hidden sm:flex flex-col items-start">
                  <span className="text-sm font-semibold text-base-primary">
                    {user.username}
                  </span>
                  <span className="text-xs text-base-tertiary">
                    {user.email?.split('@')[0]}
                  </span>
                </div>
                <ChevronDown className="h-4 w-4 text-base-secondary transition-transform duration-200" />
              </button>

              {/* Dropdown Menu */}
              {dropdownOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-10" 
                    onClick={() => setDropdownOpen(false)}
                  />
                  <div className="absolute right-0 mt-3 w-64 bg-surface/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-surface-border-hover z-20">
                    <div className="p-4 border-b border-surface-border">
                      <div className="flex items-center space-x-3">
                        <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-lg font-bold shadow-lg">
                          {getInitials(user.username)}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-base-primary">
                            {user.username}
                          </p>
                          <p className="text-xs text-base-tertiary mt-1">
                            {user.email}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="p-3 space-y-1">
                      <button
                        onClick={() => {
                          setDropdownOpen(false);
                          navigate('/profile');
                        }}
                        className="flex items-center space-x-3 px-4 py-3 text-sm font-medium text-base-primary hover:bg-primary/5 hover:text-primary rounded-xl transition-all duration-200 w-full text-left"
                      >
                        <User className="h-5 w-5" />
                        <span>Profile Settings</span>
                      </button>
                      
                      <button
                        onClick={() => {
                          setDropdownOpen(false);
                          navigate('/tokens');
                        }}
                        className="flex items-center space-x-3 px-4 py-3 text-sm font-medium text-base-primary hover:bg-primary/5 hover:text-primary rounded-xl transition-all duration-200 w-full text-left"
                      >
                        <Key className="h-5 w-5" />
                        <span>API Tokens</span>
                      </button>
                      
                      <button
                        onClick={() => {
                          setDropdownOpen(false);
                          navigate('/dashboard');
                        }}
                        className="flex items-center space-x-3 px-4 py-3 text-sm font-medium text-base-primary hover:bg-primary/5 hover:text-primary rounded-xl transition-all duration-200 md:hidden w-full text-left"
                      >
                        <Home className="h-5 w-5" />
                        <span>Dashboard</span>
                      </button>
                      
                      <div className="h-px bg-surface-border my-2"></div>
                      
                      <button
                        onClick={handleLogout}
                        className="flex items-center space-x-3 px-4 py-3 text-sm font-medium text-error hover:bg-error/5 hover:text-error-dark rounded-xl transition-all duration-200 w-full text-left"
                      >
                        <LogOut className="h-5 w-5" />
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