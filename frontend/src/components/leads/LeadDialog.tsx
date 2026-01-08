import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { leadsApi } from '@/services/api';
import { type Lead, LeadStatus } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface LeadDialogProps {
  lead: Lead | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const LeadDialog: React.FC<LeadDialogProps> = ({
  lead,
  open,
  onOpenChange,
}) => {
  const { t } = useTranslation(['common', 'leads']);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset } = useForm<Partial<Lead>>();

  useEffect(() => {
    if (lead) {
      reset(lead);
    } else {
      reset({
        customer_name: '',
        customer_email: '',
        customer_phone: '',
        customer_company: '',
        status: LeadStatus.NEW,
      });
    }
  }, [lead, reset]);

  const mutation = useMutation({
    mutationFn: (data: Partial<Lead>) =>
      lead ? leadsApi.update(lead.id, data) : leadsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      onOpenChange(false);
    },
  });

  const onSubmit = (data: Partial<Lead>) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{lead ? t('common:edit_lead') : t('common:add_lead')}</DialogTitle>
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
              <Label htmlFor="customer_phone">{t('common:customer_phone')}</Label>
              <Input id="customer_phone" {...register('customer_phone')} />
            </div>
            <div>
              <Label htmlFor="customer_company">{t('common:company')}</Label>
              <Input id="customer_company" {...register('customer_company')} />
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
                {Object.values(LeadStatus).map((status) => (
                  <option key={status} value={status}>
                    {t(`leads:status.${status}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="source">{t('common:source')}</Label>
              <Input id="source" {...register('source')} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="estimated_value">{t('common:estimated_value')}</Label>
              <Input
                id="estimated_value"
                type="number"
                step="0.01"
                {...register('estimated_value', { valueAsNumber: true })}
              />
            </div>
            <div>
              <Label htmlFor="expected_close_date">{t('common:expected_close_date')}</Label>
              <Input
                id="expected_close_date"
                type="date"
                {...register('expected_close_date')}
              />
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
