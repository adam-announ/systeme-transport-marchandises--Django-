import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  HomeIcon,
  TruckIcon,
  DocumentIcon,
  UsersIcon,
  ChartBarIcon,
  CogIcon,
  MapIcon,
  ClipboardDocumentListIcon
} from '@heroicons/react/24/outline';

const Sidebar = () => {
  const { user } = useAuth();
  const location = useLocation();

  const getMenuItems = () => {
    const baseItems = [
      { name: 'Tableau de bord', href: `/${user?.role}`, icon: HomeIcon },
    ];

    switch (user?.role) {
      case 'client':
        return [
          ...baseItems,
          { name: 'Nouvelle commande', href: '/client/commandes/new', icon: DocumentIcon },
          { name: 'Mes commandes', href: '/client/commandes', icon: ClipboardDocumentListIcon },
        ];
      
      case 'transporteur':
        return [
          ...baseItems,
          { name: 'Mes missions', href: '/transporteur/missions', icon: TruckIcon },
          { name: 'Navigation', href: '/transporteur/navigation', icon: MapIcon },
        ];
      
      case 'admin':
        return [
          ...baseItems,
          { name: 'Commandes', href: '/admin/commandes', icon: DocumentIcon },
          { name: 'Transporteurs', href: '/admin/transporteurs', icon: TruckIcon },
          { name: 'Clients', href: '/admin/clients', icon: UsersIcon },
          { name: 'Statistiques', href: '/admin/stats', icon: ChartBarIcon },
          { name: 'Paramètres', href: '/admin/settings', icon: CogIcon },
        ];
      
      case 'planificateur':
        return [
          ...baseItems,
          { name: 'Optimisation', href: '/planificateur/optimization', icon: MapIcon },
          { name: 'Assignation', href: '/planificateur/assignment', icon: TruckIcon },
          { name: 'Rapports', href: '/planificateur/reports', icon: ChartBarIcon },
        ];
      
      default:
        return baseItems;
    }
  };

  const menuItems = getMenuItems();

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
      <nav className="p-4 space-y-2">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
};

export default Sidebar;
