"use client";
import React, { useState, useEffect, useRef, ReactNode, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../contexts/AuthContext";
import { useTheme } from "../hooks/useTheme";
import { useInfoToast } from "../components/ui/toast";

const User = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const Settings = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <circle cx="12" cy="12" r="3" />
    <path d="M12 1v6m0 6v6" />
    <path d="M1 12h6m6 0h6" />
  </svg>
);


const HelpCircle = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
    <line x1="12" x2="12.01" y1="17" y2="17" />
  </svg>
);

const LogOut = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" x2="9" y1="12" y2="12" />
  </svg>
);

const Key = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" />
  </svg>
);

const Moon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
  </svg>
);

const Sun = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2" />
    <path d="M12 20v2" />
    <path d="m4.93 4.93 1.41 1.41" />
    <path d="m17.66 17.66 1.41 1.41" />
    <path d="M2 12h2" />
    <path d="M20 12h2" />
    <path d="m6.34 17.66-1.41 1.41" />
    <path d="m19.07 4.93-1.41 1.41" />
  </svg>
);

interface DropdownMenuProps {
  children: ReactNode;
  trigger: ReactNode;
}

const DropdownMenu = ({ children, trigger }: DropdownMenuProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleTriggerClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <div onClick={handleTriggerClick} className="cursor-pointer">
        {trigger}
      </div>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <div 
            className="fixed inset-0 z-[9998]" 
            onClick={() => setIsOpen(false)}
          />
          {/* Dropdown menu with higher z-index */}
          <div
            className="origin-top-right absolute right-0 mt-2 w-72 rounded-xl shadow-xl bg-white dark:bg-zinc-900 ring-1 ring-black ring-opacity-5 focus:outline-none z-[9999] animate-in fade-in-0 zoom-in-95 p-2"
            role="menu"
            aria-orientation="vertical"
            onClick={() => setIsOpen(false)}
          >
            {children}
          </div>
        </>
      )}
    </div>
  );
};

interface DropdownMenuItemProps {
  children: ReactNode;
  onClick?: () => void;
}

const DropdownMenuItem = ({ children, onClick }: DropdownMenuItemProps) => (
  <a
    href="#"
    onClick={(e: React.MouseEvent) => {
      e.preventDefault();
      if (onClick) onClick();
    }}
    className="text-zinc-700 dark:text-zinc-300 group flex items-center px-3 py-2.5 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors duration-150"
    role="menuitem"
  >
    {children}
  </a>
);

const DropdownMenuSeparator = () => (
  <div className="my-2 h-px bg-zinc-200 dark:bg-zinc-700" />
);

export default function UserProfileDropdown() {
  const authContext = useContext(AuthContext);
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const showInfoToast = useInfoToast();

  if (!authContext || !authContext.user) {
    return null;
  }

  const { user, logout } = authContext;

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleSignOut = () => {
    logout();
    navigate('/login');
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  const handleNavigation = (path: string, routeName: string) => {
    // Check if route exists
    const existingRoutes = ['/dashboard', '/profile', '/tokens'];
    
    if (existingRoutes.includes(path)) {
      navigate(path);
    } else {
      // Show notification for non-existent routes
      showInfoToast(
        `${routeName} Coming Soon`,
        'This feature will be available in a future update'
      );
    }
  };

  return (
    <DropdownMenu
      trigger={
        <button className="flex items-center space-x-3 p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
            {getInitials(user.username)}
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {user.username}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              {user.email}
            </div>
          </div>
        </button>
      }
    >
      <div className="px-3 py-3 border-b border-zinc-200 dark:border-zinc-700">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
            {getInitials(user.username)}
          </div>
          <div>
            <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {user.username}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              {user.email}
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">
              {user.roles.join(' • ')}
            </div>
          </div>
        </div>
      </div>

      <div className="py-1">
        <DropdownMenuItem onClick={() => handleNavigation('/profile', 'Profile')}>
          <User className="mr-3 h-4 w-4 text-zinc-500" />
          Your Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleNavigation('/tokens', 'API Tokens')}>
          <Key className="mr-3 h-4 w-4 text-zinc-500" />
          API Tokens
        </DropdownMenuItem>
        <DropdownMenuItem onClick={toggleTheme}>
          {theme === 'light' ? (
            <>
              <Moon className="mr-3 h-4 w-4 text-zinc-500" />
              Dark Mode
            </>
          ) : (
            <>
              <Sun className="mr-3 h-4 w-4 text-zinc-500" />
              Light Mode
            </>
          )}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleNavigation('/settings', 'Settings')}>
          <Settings className="mr-3 h-4 w-4 text-zinc-500" />
          Settings
        </DropdownMenuItem>
      </div>

      <DropdownMenuSeparator />

      <div className="py-1">
        <DropdownMenuItem onClick={() => {
          showInfoToast('Documentation Coming Soon', 'Help documentation will be available in the next release');
        }}>
          <HelpCircle className="mr-3 h-4 w-4 text-zinc-500" />
          Help & Support
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleSignOut}>
          <LogOut className="mr-3 h-4 w-4 text-zinc-500" />
          Sign Out
        </DropdownMenuItem>
      </div>
    </DropdownMenu>
  );
}