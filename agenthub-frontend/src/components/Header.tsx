import { Armchair, BookOpen, Home, Key, Menu, Moon, Network, Settings, Sun, Terminal, X } from 'lucide-react';
import React, { useContext, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { Brand } from './ui/Brand';
import { MenuBar } from './ui/glow-menu';
import UserProfileDropdown from './UserProfileDropdown';
import { WebSocketStatus } from './WebSocketStatus';
import { NotificationBell } from './NotificationBell';

export const Header: React.FC = () => {
  const authContext = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // The mobile drawer is `fixed`, so it cannot inherit the header's height from
  // flow: it measures the header itself. A declared token could not do this - the
  // header's height is its padding plus its line box, which is 77px at >=768 and
  // 73px at 390, so any literal is wrong somewhere (R2).
  const headerRef = useRef<HTMLElement | null>(null);
  const [drawerTop, setDrawerTop] = useState(0);

  useEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const measure = (): void => setDrawerTop(header.offsetHeight);
    measure();
    // The observer is what keeps the value honest. The brand font landing after
    // mount moves the header from 64px to 73px at 390, and a resize or a zoom moves
    // it again, so a one-shot read on open would freeze a half-laid-out height -
    // which is exactly what a first run measured (drawer 64px under a 73px header).
    const observer = new ResizeObserver(measure);
    observer.observe(header);
    window.addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, []);

  if (!authContext) {
    return null;
  }

  const { user } = authContext;

  // Labels and destinations only. The eight per-item gradient/icon pairs that used
  // to live here are retired (F-5): the shell paints one accent from the token
  // layer, so the glow menu no longer takes a colour per item.
  const menuItems = [
    { icon: Home, label: "Dashboard", href: "/dashboard" },
    { icon: Key, label: "Tokens", href: "/tokens" },
    { icon: Armchair, label: "Seats", href: "/seats" },
    { icon: Terminal, label: "Sessions", href: "/sessions" },
    { icon: Network, label: "Topology", href: "/topology" },
    { icon: BookOpen, label: "Docs", href: "/docs" },
    { icon: Settings, label: "Settings", href: "/profile" },
    {
      icon: theme === 'dark' ? Sun : Moon,
      label: theme === 'dark' ? "Light" : "Dark",
      href: "#theme-toggle",
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
      <header
        ref={headerRef}
        className="theme-nav px-4 sm:px-6 py-3 shadow-lg backdrop-blur-xl bg-surface/95 border-b border-surface-border transition-theme relative z-[1000]"
      >
        <div className="flex items-center justify-between">
          {/* Brand Section - one line, so the navigation beside it has the room (F-1) */}
          <div className="flex items-center">
            <Link
              to="/dashboard"
              className="flex items-baseline gap-2 sm:gap-3 group whitespace-nowrap"
            >
              <Brand variant="header" />
              {/* The sub-label yields to the navigation that shares its band.
                  Beside the brand it costs ~128px, and from md to 1023 the
                  tablet icon nav is already in the row, which is where the
                  header row ran wider than the baseline (A3). The muted text
                  role replaces the inert text-black-* classes it carried. */}
              <span className="text-xs text-text-secondary hidden sm:block md:hidden">
                AI Orchestration Platform
              </span>
            </Link>
          </div>

          {user ? (
            <div className="flex items-center space-x-2">
              {/* WebSocket Status Indicator */}
              <WebSocketStatus />

              {/* Dashboard push: notifications sent to this user */}
              <NotificationBell />

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
                    to="/seats"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Seats"
                  >
                    <Armchair className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/sessions"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Sessions"
                  >
                    <Terminal className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/topology"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Topology"
                  >
                    <Network className="h-5 w-5" />
                  </Link>
                  <Link
                    to="/docs"
                    className="flex items-center p-2 rounded-lg theme-nav-item transition-all duration-200 hover:bg-primary/10 hover:text-primary"
                    title="Docs"
                  >
                    <BookOpen className="h-5 w-5" />
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

          {/* Mobile Menu: `top` is the header's own measured height, observed on the
              header itself so a late font, a resize or a zoom cannot leave it stale. */}
          <div
            style={{ top: drawerTop }}
            className="fixed left-0 right-0 bg-surface/95 backdrop-blur-xl border-b border-surface-border shadow-lg z-[999] md:hidden animate-slide-in"
          >
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
                      <Icon className="h-5 w-5" />
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
                    <Icon className="h-5 w-5" />
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
