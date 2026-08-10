import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  Users,
  LogOut,
  Wrench,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/tasks", icon: ClipboardList, label: "Tasks" },
  { to: "/workers", icon: Users, label: "Workers" },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
      isActive
        ? "bg-brand-600 text-white"
        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
    }`;

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600">
          <Wrench className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-gray-900">Field Service</p>
          <p className="text-xs text-gray-500">Manager Portal</p>
        </div>
      </div>

      <div className="mx-3 mb-4 h-px bg-gray-100" />

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={navLinkClass}
            onClick={() => setMobileOpen(false)}
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="mx-3 mt-4 h-px bg-gray-100" />
      <div className="p-3">
        <div className="mb-2 rounded-lg bg-gray-50 px-3 py-2.5">
          <p className="truncate text-sm font-medium text-gray-900">
            {user?.full_name}
          </p>
          <p className="truncate text-xs text-gray-500">{user?.email}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 border-r border-gray-200 bg-white lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-60 bg-white transition-transform lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex justify-end p-2 lg:hidden">
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <SidebarContent />
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile topbar */}
        <header className="flex h-14 items-center gap-3 border-b border-gray-200 bg-white px-4 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-gray-800">
            Field Service
          </span>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
