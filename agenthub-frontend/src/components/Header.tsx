import { Home, HelpCircle, Key, Moon, Settings, Sun, Menu, X } from 'lucide-react';
import React, { useContext, useState } from 'react';
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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
      icon: HelpCircle,
      label: "Help & Setup",
      href: "/help",
      gradient: "radial-gradient(circle, rgba(168,85,247,0.15) 0%, rgba(147,51,234,0.06) 50%, rgba(124,58,237,0) 100%)",
      iconColor: "text-purple-500",
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
    <>
      <header className="theme-nav px-4 sm:px-6 py-3 sm:py-4 shadow-lg backdrop-blur-xl bg-surface/95 border-b border-surface-border transition-theme relative z-[1000]">
        <div className="flex items-center justify-between">
          {/* Brand Section - Responsive */}
          <div className="flex items-center">
            <Link to="/dashboard" className="flex items-center space-x-2 sm:space-x-3 group">
              <div className="flex flex-col">
                <Brand variant="header" />
                <span className="text-xs text-black-600 dark:text-black-200 -mt-1 hidden sm:block">
                  AI Orchestration Platform
                </span>
              </div>
            </Link>
          </div>

          {user ? (
            <div className="flex items-center space-x-2 sm:space-x-4">
              {/* Desktop/Tablet Glow Menu Navigation */}
              <div className="hidden lg:block">
                <MenuBar
                  items={menuItems}
                  activeItem={getActiveItem()}
                  onItemClick={handleMenuClick}
                />
              </div>

              {/* Tablet Navigation - Condensed */}
              <div className="hidden md:block lg:hidden">
                <nav className="flex items-center space-x-1">
                  <Link
                    to="/dashboard"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Dashboard"
                  >
                    <Home className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/tokens"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Tokens"
                  >
                    <Key className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/help"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Help & Setup"
                  >
                    <HelpCircle className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/profile"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Settings"
                  >
                    <Settings className="h-5 w-5" />
                  </Link>
                  <button
                    onClick={toggleTheme}
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title={theme === 'dark' ? "Light Mode" : "Dark Mode"}
                  >
                    {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                  </button>
                </nav>
              </div>

              {/* Mobile Hamburger Menu Button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden flex items-center justify-center w-10 h-10 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                aria-label="Toggle mobile menu"
              >
                {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>

              {/* User Profile Dropdown */}
              <UserProfileDropdown />
            </div>
          ) : (
            /* Show theme toggle for non-authenticated users */
            <div className="flex items-center space-x-2">
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
              {/* Mobile theme toggle for non-authenticated users */}
              <button
                onClick={toggleTheme}
                className="md:hidden flex items-center justify-center w-10 h-10 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                aria-label={theme === 'dark' ? "Switch to light mode" : "Switch to dark mode"}
              >
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && user && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[999] md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />

          {/* Mobile Menu */}
          <div className="fixed top-[73px] left-0 right-0 bg-surface/95 backdrop-blur-xl border-b border-surface-border shadow-lg z-[999] md:hidden animate-slide-in">
            <nav className="px-4 py-6 space-y-2">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = item.label === getActiveItem();

                if (item.href === "#theme-toggle") {
                  return (
                    <button
                      key={item.label}
                      onClick={() => {
                        toggleTheme();
                        setIsMobileMenuOpen(false);
                      }}
                      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 hover:bg-primary/10 hover:text-primary ${
                        isActive ? 'bg-primary/10 text-primary' : 'theme-nav-item'
                      }`}
                    >
                      <Icon className={`h-5 w-5 ${item.iconColor}`} />
                      <span className="font-medium">{item.label}</span>
                    </button>
                  );
                }

                return (
                  <Link
                    key={item.label}
                    to={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 hover:bg-primary/10 hover:text-primary ${
                      isActive ? 'bg-primary/10 text-primary' : 'theme-nav-item'
                    }`}
                  >
                    <Icon className={`h-5 w-5 ${item.iconColor}`} />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </>
      )}
    </>
  );
};