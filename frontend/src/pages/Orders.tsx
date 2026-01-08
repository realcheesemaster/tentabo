import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ordersApi } from '@/services/api';
import { type Order } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Plus } from 'lucide-react';
import { DataTable, type Column } from '@/components/common/DataTable';
import { OrderDialog } from '@/components/orders/OrderDialog';

export const Orders: React.FC = () => {
  const { t } = useTranslation(['orders', 'common']);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data: orders, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => ordersApi.getAll(),
  });

  const columns: Column<Order>[] = [
    {
      key: 'order_number',
      header: t('order_number'),
    },
    {
      key: 'customer_name',
      header: t('common:customer_name'),
    },
    {
      key: 'customer_email',
      header: t('common:customer_email'),
    },
    {
      key: 'status',
      header: t('common:status'),
      render: (order) => <StatusBadge status={order.status} type="order" />,
    },
    {
      key: 'total_amount',
      header: t('total_amount'),
      render: (order) => formatCurrency(order.total_amount, order.currency),
    },
    {
      key: 'created_at',
      header: t('common:created_at'),
      render: (order) => formatDate(order.created_at),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground">{t('common:manage_customer_orders')}</p>
        </div>
        <Button
          onClick={() => {
            setSelectedOrder(null);
            setIsDialogOpen(true);
          }}
        >
          <Plus className="h-4 w-4 mr-2" />
          {t('add_order')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={orders || []}
            columns={columns}
            onRowClick={(order) => {
              setSelectedOrder(order);
              setIsDialogOpen(true);
            }}
          />
        </CardContent>
      </Card>

      <OrderDialog
        order={selectedOrder}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
};
