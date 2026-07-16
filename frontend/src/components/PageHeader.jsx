export default function PageHeader({ title, subtitle, children }) {
  return (
    <div className="sticky top-0 z-10 flex flex-col gap-3 border-b border-slate-200/70 bg-white/70 px-6 py-4 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
