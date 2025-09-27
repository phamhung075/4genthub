# Glow Menu Component Usage Guide

## Overview
The `glow-menu.tsx` component is a modern, animated navigation menu with glow effects, perfect for React applications using Tailwind CSS and Framer Motion.

## Features
- ✨ Smooth 3D flip animations on hover
- 🌈 Dynamic glow effects with customizable colors
- 🎨 Theme-aware design (supports light/dark modes)
- 📱 Responsive design considerations
- ⚡ Framer Motion powered animations
- 🧩 TypeScript support with full type safety

## Dependencies
Already installed in this project:
- `framer-motion` (v12.23.12)
- `lucide-react` (v0.525.0)
- Custom theme hook: `@/hooks/useTheme`
- Utility function: `@/lib/utils` (cn function)

## Basic Usage

### 1. Import the Component
```tsx
import { MenuBar } from '@/components/ui/glow-menu';
import { Home, Settings, Bell, User } from 'lucide-react';
```

### 2. Define Menu Items
```tsx
const menuItems = [
  {
    icon: Home,
    label: "Dashboard",
    href: "/dashboard",
    gradient: "radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(37,99,235,0.06) 50%, rgba(29,78,216,0) 100%)",
    iconColor: "text-blue-500",
  },
  {
    icon: Settings,
    label: "Settings", 
    href: "/settings",
    gradient: "radial-gradient(circle, rgba(34,197,94,0.15) 0%, rgba(22,163,74,0.06) 50%, rgba(21,128,61,0) 100%)",
    iconColor: "text-green-500",
  },
  // ... more items
];
```

### 3. Use with Router Integration
```tsx
import { useLocation, useNavigate } from 'react-router-dom';

export function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();

  const getActiveItem = () => {
    const currentPath = location.pathname;
    const activeItem = menuItems.find(item => item.href === currentPath);
    return activeItem ? activeItem.label : "Dashboard";
  };

  const handleMenuClick = (label: string) => {
    const menuItem = menuItems.find(item => item.label === label);
    if (menuItem) {
      navigate(menuItem.href);
    }
  };

  return (
    <MenuBar
      items={menuItems}
      activeItem={getActiveItem()}
      onItemClick={handleMenuClick}
    />
  );
}
```

## Props Interface

### MenuBar Props
```tsx
interface MenuBarProps extends React.HTMLAttributes<HTMLDivElement> {
  items: MenuItem[]
  activeItem?: string
  onItemClick?: (label: string) => void
}
```

### MenuItem Interface
```tsx
interface MenuItem {
  icon: LucideIcon | React.FC    // Lucide icon component
  label: string                  // Display text
  href: string                   // Route path
  gradient: string               // CSS gradient for glow effect
  iconColor: string              // Tailwind color class for icon
}
```

## Customization Options

### Color Gradients
Each menu item supports custom gradients for the glow effect:
- **Blue**: `rgba(59,130,246,0.15)` → `rgba(29,78,216,0)`
- **Green**: `rgba(34,197,94,0.15)` → `rgba(21,128,61,0)`
- **Orange**: `rgba(249,115,22,0.15)` → `rgba(194,65,12,0)`
- **Red**: `rgba(239,68,68,0.15)` → `rgba(185,28,28,0)`

### Icon Colors
Use Tailwind color utilities:
- `text-blue-500`, `text-green-500`, `text-orange-500`, `text-red-500`

### Theme Support
The component automatically adapts to light/dark themes using the existing theme context.

## Real-World Implementation

This component is integrated into the Header component (`src/components/Header.tsx`) and replaces traditional navigation with:
- Modern glow effects
- 3D hover animations  
- Smooth transitions
- Responsive mobile fallback

## Styling Notes

### Required Tailwind Config
Make sure your `tailwind.config.js` includes:
```js
extend: {
  backgroundImage: {
    'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
  },
}
```

### CSS Classes Used
- `backdrop-blur-lg` - Background blur effect
- `bg-gradient-radial` - Radial gradient support
- `perspective` styles - 3D transformation effects
- Theme-aware colors via CSS variables

## Performance Considerations

- Uses `React.forwardRef` for proper ref forwarding
- Optimized animations with Framer Motion
- Smooth transitions with spring physics
- Minimal re-renders with proper memoization

## Browser Support

- Modern browsers with CSS backdrop-filter support
- Graceful degradation for older browsers
- Mobile-responsive design patterns

## Accessibility Features

- Semantic HTML structure
- Keyboard navigation support
- Screen reader friendly
- Focus management
- Color contrast compliance