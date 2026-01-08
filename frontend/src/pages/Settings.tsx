import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { providersApi } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';

export const Settings: React.FC = () => {
  const { t } = useTranslation('common');

  const { data: providers, isLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: () => providersApi.getAll(),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('settings')}</h1>
        <p className="text-muted-foreground">{t('configure_system_settings')}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('provider_configuration')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {providers?.map((provider) => (
              <div
                key={provider.id}
                className="flex items-center justify-between border-b pb-4"
              >
                <div>
                  <div className="font-medium">{provider.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {t('type')}: {provider.provider_type}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {t('updated')}: {formatDate(provider.updated_at)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={provider.is_active ? 'success' : 'secondary'}>
                    {provider.is_active ? t('active') : t('inactive')}
                  </Badge>
                  <Button variant="outline" size="sm">
                    {t('configure')}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
