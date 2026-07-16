import { motion } from "framer-motion";
import { classNames } from "../lib/ui.js";

export function Card({ className, children, hover = false, ...rest }) {
  return (
    <div
      className={classNames(
        "rounded-2xl bg-white/85 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm",
        hover && "transition duration-300 hover:-translate-y-0.5 hover:shadow-soft hover:ring-slate-300/70",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

// Staggered entrance wrapper for grids/lists.
export const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};
export const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 260, damping: 24 } },
};

export function MotionCard({ className, children, hover = true, ...rest }) {
  return (
    <motion.div
      variants={rise}
      className={classNames(
        "rounded-2xl bg-white/85 shadow-card ring-1 ring-slate-200/70 backdrop-blur-sm",
        hover && "transition-shadow duration-300 hover:shadow-soft",
        className
      )}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function Chip({ className, children }) {
  return (
    <span
      className={classNames(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset",
        className
      )}
    >
      {children}
    </span>
  );
}

export function Avatar({ name, colorClass, size = "md", ring = false }) {
  const dim = size === "sm" ? "h-8 w-8 text-xs" : size === "lg" ? "h-12 w-12 text-base" : "h-10 w-10 text-sm";
  return (
    <div
      className={classNames(
        "flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-bold text-white shadow-sm",
        colorClass,
        dim,
        ring && "ring-2 ring-white"
      )}
    >
      {name}
    </div>
  );
}

export function Spinner({ className }) {
  return (
    <svg
      className={classNames("animate-spin text-brand-500", className || "h-5 w-5")}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

export function Skeleton({ className }) {
  return <div className={classNames("skeleton rounded-xl", className)} />;
}

export function EmptyState({ icon: Icon, title, subtitle }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center gap-3 py-16 text-center"
    >
      {Icon && (
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 text-slate-400 shadow-inner">
          <Icon className="h-7 w-7" />
        </div>
      )}
      <div>
        <p className="font-semibold text-slate-700">{title}</p>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
    </motion.div>
  );
}

export function Button({ variant = "primary", className, children, ...rest }) {
  const styles = {
    primary:
      "bg-gradient-to-b from-brand-500 to-brand-600 text-white shadow-sm hover:from-brand-500 hover:to-brand-700 hover:shadow-glow active:scale-[0.98]",
    ghost: "bg-white/80 text-slate-700 ring-1 ring-slate-200 hover:bg-white hover:ring-slate-300 active:scale-[0.98]",
    subtle: "bg-slate-100 text-slate-600 hover:bg-slate-200 active:scale-[0.98]",
    dark: "bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98]",
  };
  return (
    <button
      className={classNames(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        styles[variant],
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
