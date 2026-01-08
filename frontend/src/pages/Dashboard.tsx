import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { dashboardApi } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Package, ShoppingCart, FileText, TrendingUp } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { t } = useTranslation('common');

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: dashboardApi.getMetrics,
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('dashboard')}</h1>
        <p className="text-muted-foreground">{t('welcome')}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('leads')}</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_leads || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('orders')}</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_orders || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('contracts')}</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.active_contracts || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('revenue')}</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(metrics?.total_revenue || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t('recent_leads')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.recent_leads && metrics.recent_leads.length > 0 ? (
                metrics.recent_leads.slice(0, 5).map((lead) => (
                  <div key={lead.id} className="flex items-center justify-between border-b pb-2">
                    <div>
                      <div className="font-medium">{lead.customer_name}</div>
                      <div className="text-sm text-muted-foreground">{lead.customer_email}</div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatDate(lead.created_at)}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">{t('no_recent_leads')}</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('recent_orders')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.recent_orders && metrics.recent_orders.length > 0 ? (
                metrics.recent_orders.slice(0, 5).map((order) => (
                  <div key={order.id} className="flex items-center justify-between border-b pb-2">
                    <div>
                      <div className="font-medium">{order.order_number}</div>
                      <div className="text-sm text-muted-foreground">{order.customer_name}</div>
                    </div>
                    <div className="text-sm font-medium">
                      {formatCurrency(order.total_amount)}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">{t('no_recent_orders')}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
