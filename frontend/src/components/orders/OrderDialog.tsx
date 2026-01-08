import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ordersApi, productsApi } from '@/services/api';
import { type Order, OrderStatus } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface OrderDialogProps {
  order: Order | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const OrderDialog: React.FC<OrderDialogProps> = ({
  order,
  open,
  onOpenChange,
}) => {
  const { t } = useTranslation(['common', 'orders']);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset } = useForm<Partial<Order>>();

  useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
    enabled: open,
  });

  useEffect(() => {
    if (order) {
      reset(order);
    } else {
      reset({
        customer_name: '',
        customer_email: '',
        status: OrderStatus.DRAFT,
        currency: 'EUR',
        items: [],
      });
    }
  }, [order, reset]);

  const mutation = useMutation({
    mutationFn: (data: Partial<Order>) =>
      order ? ordersApi.update(order.id, data) : ordersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      onOpenChange(false);
    },
  });

  const onSubmit = (data: Partial<Order>) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{order ? t('common:edit_order') : t('common:create_order')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="customer_name">{t('common:customer_name')}</Label>
              <Input id="customer_name" {...register('customer_name', { required: true })} />
            </div>
            <div>
              <Label htmlFor="customer_email">{t('common:customer_email')}</Label>
              <Input
                id="customer_email"
                type="email"
                {...register('customer_email', { required: true })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="status">{t('common:status')}</Label>
              <select
                id="status"
                {...register('status')}
                className="flex h-10 w-full rounded-md border border-input bg-background text-foreground px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                {Object.values(OrderStatus).map((status) => (
                  <option key={status} value={status}>
                    {t(`orders:status.${status}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="currency">{t('common:currency')}</Label>
              <select
                id="currency"
                {...register('currency')}
                className="flex h-10 w-full rounded-md border border-input bg-background text-foreground px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="notes">{t('common:notes')}</Label>
            <textarea
              id="notes"
              {...register('notes')}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background text-foreground px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('common:cancel')}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? t('common:saving') : t('common:save')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
