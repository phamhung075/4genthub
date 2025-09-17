import { Home, Key, Moon, Settings, Sun } from 'lucide-react';
import React, { useContext } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { Brand } from './ui/Brand';
import { MenuBar } from './ui/glow-menu';
import UserProfileDropdown from './UserProfileDropdown';

export const Header: React.FC = () => {
  const authContext = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  if (!authContext) {
    return null;
  }

  const { user } = authContext;

  // Define menu items for the glow menu with original vibrant colors
  const menuItems = [
    {
      icon: Home,
      label: "Dashboard",
      href: "/dashboard",
      gradient: "radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(37,99,235,0.06) 50%, rgba(29,78,216,0) 100%)",
      iconColor: "text-blue-500",
    },
    //{
    //  icon: Activity,
    //  label: "Performance",
    //  href: "/performance",
    //  gradient: "radial-gradient(circle, rgba(236,72,153,0.15) 0%, rgba(219,39,119,0.06) 50%, rgba(190,24,93,0) 100%)",
    //  iconColor: "text-pink-500",
    //},
    {
      icon: Key,
      label: "Tokens",
      href: "/tokens",
      gradient: "radial-gradient(circle, rgba(249,115,22,0.15) 0%, rgba(234,88,12,0.06) 50%, rgba(194,65,12,0) 100%)",
      iconColor: "text-orange-500",
    },
    {
      icon: Settings,
      label: "Settings",
      href: "/profile",
      gradient: "radial-gradient(circle, rgba(34,197,94,0.15) 0%, rgba(22,163,74,0.06) 50%, rgba(21,128,61,0) 100%)",
      iconColor: "text-green-500",
    },
    {
      icon: theme === 'dark' ? Sun : Moon,
      label: theme === 'dark' ? "Light" : "Dark",
      href: "#theme-toggle",
      gradient: "radial-gradient(circle, rgba(139,69,19,0.15) 0%, rgba(120,53,15,0.06) 50%, rgba(101,38,10,0) 100%)",
      iconColor: theme === 'dark' ? "text-yellow-500" : "text-indigo-500",
    },
  ];

  // Get the current active item based on the current route
  const getActiveItem = () => {
    const currentPath = location.pathname;
    const activeItem = menuItems.find(item => item.href === currentPath);
    return activeItem ? activeItem.label : "Dashboard";
  };

  // Handle navigation when menu item is clicked
  const handleMenuClick = (label: string) => {
    const menuItem = menuItems.find(item => item.label === label);
    if (menuItem) {
      // Handle theme toggle
      if (menuItem.href === "#theme-toggle") {
        toggleTheme();
        return;
      }
      // Handle regular navigation
      navigate(menuItem.href);
    }
  };

  return (
    <header className="theme-nav px-6 py-4 shadow-lg backdrop-blur-xl bg-surface/95 border-b border-surface-border transition-theme relative z-[1000]">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/dashboard" className="flex items-center space-x-3 group">

            <div className="flex flex-col">
              <Brand variant="header" />
              <span className="text-xs text-black-600 dark:text-black-200 -mt-1">AI Orchestration Platform</span>
            </div>
          </Link>
        </div>
        
        {user ? (
          <div className="flex items-center space-x-4">
            {/* Glow Menu Navigation */}
            <div className="hidden md:block">
              <MenuBar
                items={menuItems}
                activeItem={getActiveItem()}
                onItemClick={handleMenuClick}
              />
            </div>

            {/* Mobile fallback navigation */}
            <nav className="flex md:hidden items-center space-x-2">
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

            {/* User Profile Dropdown */}
            <UserProfileDropdown />
          </div>
        ) : (
          /* Show theme toggle for non-authenticated users */
          <div className="hidden md:block">
            <MenuBar
              items={[{
                icon: theme === 'dark' ? Sun : Moon,
                label: theme === 'dark' ? "Light" : "Dark",
                href: "#theme-toggle",
                gradient: "radial-gradient(circle, rgba(139,69,19,0.15) 0%, rgba(120,53,15,0.06) 50%, rgba(101,38,10,0) 100%)",
                iconColor: theme === 'dark' ? "text-yellow-500" : "text-indigo-500",
              }]}
              activeItem=""
              onItemClick={handleMenuClick}
            />
          </div>
        )}
      </div>
    </header>
  );
};