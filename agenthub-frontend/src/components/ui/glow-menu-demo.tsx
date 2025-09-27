"use client"

import { useState } from "react"
import { Home, Settings, Key, User, Sun, Moon } from "lucide-react"
import { MenuBar } from "./glow-menu"
import { useTheme } from "../../hooks/useTheme"

export function MenuBarDemo() {
  const [activeItem, setActiveItem] = useState<string>("Dashboard")
  const { theme, toggleTheme } = useTheme()

  const menuItems = [
    {
      icon: Home,
      label: "Dashboard",
      href: "/dashboard",
      gradient: "radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(37,99,235,0.06) 50%, rgba(29,78,216,0) 100%)",
      iconColor: "text-blue-500",
    },
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
      href: "/settings",
      gradient: "radial-gradient(circle, rgba(34,197,94,0.15) 0%, rgba(22,163,74,0.06) 50%, rgba(21,128,61,0) 100%)",
      iconColor: "text-green-500",
    },
    {
      icon: User,
      label: "Profile",
      href: "/profile",
      gradient: "radial-gradient(circle, rgba(239,68,68,0.15) 0%, rgba(220,38,38,0.06) 50%, rgba(185,28,28,0) 100%)",
      iconColor: "text-red-500",
    },
    {
      icon: theme === 'dark' ? Sun : Moon,
      label: theme === 'dark' ? "Light" : "Dark",
      href: "#theme-toggle",
      gradient: "radial-gradient(circle, rgba(139,69,19,0.15) 0%, rgba(120,53,15,0.06) 50%, rgba(101,38,10,0) 100%)",
      iconColor: theme === 'dark' ? "text-yellow-500" : "text-indigo-500",
    },
  ]

  const handleMenuClick = (label: string) => {
    const menuItem = menuItems.find(item => item.label === label);
    if (menuItem?.href === "#theme-toggle") {
      toggleTheme();
      return;
    }
    setActiveItem(label);
  }

  return (
    <MenuBar
      items={menuItems}
      activeItem={activeItem}
      onItemClick={handleMenuClick}
    />
  )
}