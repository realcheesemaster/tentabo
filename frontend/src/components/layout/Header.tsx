import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { LogOut, Menu, Globe } from 'lucide-react';

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { t, i18n } = useTranslation('common');
  const { user, logout } = useAuth();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'fr' ? 'en' : 'fr';
    i18n.changeLanguage(newLang);
  };

  return (
    <header className="h-16 border-b bg-card px-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" onClick={onToggleSidebar}>
            <Menu className="h-5 w-5" />
          </Button>
        )}
      </div>

      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={toggleLanguage}>
          <Globe className="h-4 w-4 mr-2" />
          {i18n.language.toUpperCase()}
        </Button>

        <div className="text-sm">
          <div className="font-medium">{user?.full_name || user?.username}</div>
          <div className="text-xs text-muted-foreground">
            {t(`role.${user?.role}`)}
          </div>
        </div>

        <Button variant="ghost" size="sm" onClick={logout}>
          <LogOut className="h-4 w-4 mr-2" />
          {t('logout')}
        </Button>
      </div>
    </header>
  );
};
