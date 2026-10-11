"use client"

import * as React from "react"
import { motion, type Transition, type Variants } from "framer-motion"
import { useTheme } from "@/hooks/useTheme"
import { cn } from "@/lib/utils"
import { LucideIcon } from "lucide-react"

interface MenuItem {
  icon: LucideIcon | React.FC
  label: string
  href: string
}

type MenuBarProps = React.ComponentPropsWithoutRef<typeof motion.nav> & {
  items: MenuItem[]
  activeItem?: string
  onItemClick?: (label: string) => void
}

const itemVariants: Variants = {
  initial: { rotateX: 0, opacity: 1 },
  hover: { rotateX: -90, opacity: 0 },
}

const backVariants: Variants = {
  initial: { rotateX: 90, opacity: 0 },
  hover: { rotateX: 0, opacity: 1 },
}

const glowVariants: Variants = {
  initial: { opacity: 0, scale: 0.8 },
  hover: {
    opacity: 1,
    scale: 2,
    transition: {
      opacity: { duration: 0.5, ease: [0.4, 0, 0.2, 1] as const },
      scale: { duration: 0.5, type: "spring", stiffness: 300, damping: 25 },
    },
  },
}

const navGlowVariants: Variants = {
  initial: { opacity: 0 },
  hover: {
    opacity: 1,
    transition: {
      duration: 0.5,
      ease: [0.4, 0, 0.2, 1] as const,
    },
  },
}

const sharedTransition: Transition = {
  type: "spring",
  stiffness: 100,
  damping: 20,
  duration: 0.5,
}

export const MenuBar = React.forwardRef<React.ElementRef<typeof motion.nav>, MenuBarProps>(
  ({ className, items, activeItem, onItemClick, ...props }, ref) => {
    const { theme } = useTheme()
    const isDarkTheme = theme === "dark"

    return (
      <motion.nav
        ref={ref}
        className={cn(
          "p-1 rounded-xl bg-surface/80 backdrop-blur-xl relative overflow-hidden transition-all duration-300",
          className,
        )}
        initial="initial"
        whileHover="hover"
        {...props}
      >
        <motion.div
          className={`absolute -inset-1 bg-gradient-radial from-transparent ${
            isDarkTheme
              ? "via-slate-400/8 via-40% via-slate-500/5 via-70%"
              : "via-slate-300/8 via-40% via-slate-400/5 via-70%"
          } to-transparent rounded-xl z-0 pointer-events-none`}
          variants={navGlowVariants}
        />
        <ul className="flex items-center gap-0.5 w-max relative z-10">
          {items.map((item) => {
            const Icon = item.icon
            const isActive = item.label === activeItem

            return (
              <motion.li key={item.label} className="relative">
                <button
                  onClick={() => onItemClick?.(item.label)}
                  className="block w-full"
                >
                  <motion.div
                    className="block rounded-xl overflow-visible group relative"
                    style={{ perspective: "600px" }}
                    whileHover="hover"
                    initial="initial"
                  >
                    <motion.div
                      className="absolute inset-0 z-0 pointer-events-none"
                      variants={glowVariants}
                      animate={isActive ? "hover" : "initial"}
                      style={{
                        // One glow for every item, from the token layer. The eight
                        // per-item hues and their radial gradients are retired (F-5):
                        // the affordance stays, the colour family does not fork.
                        background: "var(--nav-glow)",
                        opacity: isActive ? 1 : 0,
                        borderRadius: "16px",
                      }}
                    />
                    <motion.div
                      className={cn(
                        "flex items-center gap-1.5 px-2 py-2 whitespace-nowrap relative z-10 bg-transparent transition-colors rounded-lg",
                        isActive
                          ? "text-nav-text-active"
                          : "text-nav-text group-hover:text-nav-text-hover",
                      )}
                      variants={itemVariants}
                      transition={sharedTransition}
                      style={{
                       transformStyle: "preserve-3d",
                        transformOrigin: "center bottom",
                      }}
                    >
                      <span
                        className={cn(
                          "transition-colors duration-300",
                          isActive ? "text-accent" : "text-nav-text",
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      <span className="text-sm font-medium">{item.label}</span>
                    </motion.div>
                    <motion.div
                      className={cn(
                        "flex items-center gap-1.5 px-2.5 py-2 whitespace-nowrap absolute inset-0 z-10 bg-transparent transition-colors rounded-lg",
                        isActive
                          ? "text-nav-text-active"
                          : "text-nav-text group-hover:text-nav-text-hover",
                      )}
                      variants={backVariants}
                      transition={sharedTransition}
                      style={{
                        transformStyle: "preserve-3d",
                        transformOrigin: "center top",
                        rotateX: 90,
                      }}
                    >
                      <span
                        className={cn(
                          "transition-colors duration-300",
                          isActive ? "text-accent" : "text-nav-text",
                        )}
                      >
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      <span className="text-sm font-medium">{item.label}</span>
                    </motion.div>
                  </motion.div>
                </button>
              </motion.li>
            )
          })}
        </ul>
      </motion.nav>
    )
  },
)

MenuBar.displayName = "MenuBar"
