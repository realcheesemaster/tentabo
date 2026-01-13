import React from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types';
import {
  LayoutDashboard,
  Package,
  Tags,
  Users,
  Building2,
  UserCheck,
  ClipboardList,
  ShoppingCart,
  FileText,
  Settings,
  Link2,
  FileCheck,
  CalendarClock,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  roles: UserRole[];
  section?: string;
}

export const Sidebar: React.FC<{ collapsed?: boolean }> = ({ collapsed = false }) => {
  const { t } = useTranslation(['common', 'pennylane']);
  const { user } = useAuth();

  const navItems: NavItem[] = [
    {
      href: '/dashboard',
      label: t('nav.dashboard'),
      icon: <LayoutDashboard className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.DISTRIBUTOR, UserRole.PARTNER],
    },
    {
      href: '/products',
      label: t('nav.products'),
      icon: <Package className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
    },
    {
      href: '/product-types',
      label: t('nav.product_types'),
      icon: <Tags className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
    },
    {
      href: '/users',
      label: t('nav.users'),
      icon: <Users className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.RESTRICTED_ADMIN],
    },
    {
      href: '/distributors',
      label: t('nav.distributors'),
      icon: <Building2 className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
    },
    {
      href: '/partners',
      label: t('nav.partners'),
      icon: <UserCheck className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.DISTRIBUTOR],
    },
    {
      href: '/leads',
      label: t('nav.leads'),
      icon: <ClipboardList className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.DISTRIBUTOR, UserRole.PARTNER],
    },
    {
      href: '/orders',
      label: t('nav.orders'),
      icon: <ShoppingCart className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.DISTRIBUTOR, UserRole.PARTNER],
    },
    {
      href: '/contracts',
      label: t('nav.contracts'),
      icon: <FileText className="h-5 w-5" />,
      roles: [UserRole.ADMIN, UserRole.DISTRIBUTOR, UserRole.PARTNER],
    },
    {
      href: '/settings',
      label: t('nav.settings'),
      icon: <Settings className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
    },
    // Pennylane section
    {
      href: '/pennylane/connections',
      label: t('pennylane:connections'),
      icon: <Link2 className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
      section: 'pennylane',
    },
    {
      href: '/pennylane/customers',
      label: t('pennylane:customers'),
      icon: <Users className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
      section: 'pennylane',
    },
    {
      href: '/pennylane/invoices',
      label: t('pennylane:invoices'),
      icon: <FileText className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
      section: 'pennylane',
    },
    {
      href: '/pennylane/quotes',
      label: t('pennylane:quotes'),
      icon: <FileCheck className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
      section: 'pennylane',
    },
    {
      href: '/pennylane/subscriptions',
      label: t('pennylane:subscriptions'),
      icon: <CalendarClock className="h-5 w-5" />,
      roles: [UserRole.ADMIN],
      section: 'pennylane',
    },
  ];

  const filteredNavItems = navItems.filter((item) => {
    if (!user) return false;

    // Admin users (user_type === 'admin') can see everything marked for ADMIN role
    if (user.user_type === 'admin') {
      return item.roles.includes(UserRole.ADMIN);
    }

    // Regular users check their role
    return user.role ? item.roles.includes(user.role) : false;
  });

  return (
    <div
      className={cn(
        'h-screen bg-card border-r transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex flex-col h-full">
        <div className="p-4 border-b">
          <h1 className={cn('font-bold text-xl', collapsed && 'text-center')}>
            {collapsed ? 'TP' : t('app_name')}
          </h1>
        </div>
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {filteredNavItems.map((item, index) => {
              const prevItem = filteredNavItems[index - 1];
              const showSectionHeader = item.section && item.section !== prevItem?.section;

              return (
                <React.Fragment key={item.href}>
                  {showSectionHeader && (
                    <li className={cn('pt-4 pb-2', collapsed ? 'px-0' : 'px-3')}>
                      {!collapsed && (
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                          {t(`${item.section}:${item.section}`)}
                        </span>
                      )}
                      {collapsed && (
                        <div className="border-t border-border mx-2" />
                      )}
                    </li>
                  )}
                  <li>
                    <NavLink
                      to={item.href}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                          'hover:bg-accent hover:text-accent-foreground',
                          isActive && 'bg-accent text-accent-foreground font-medium',
                          collapsed && 'justify-center'
                        )
                      }
                      title={collapsed ? item.label : undefined}
                    >
                      {item.icon}
                      {!collapsed && <span>{item.label}</span>}
                    </NavLink>
                  </li>
                </React.Fragment>
              );
            })}
          </ul>
        </nav>
      </div>
    </div>
  );
};
