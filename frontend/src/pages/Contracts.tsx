import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { contractsApi, pennylaneApi } from '@/services/api';
import { type Contract, type ContractCreateRequest, type PennylaneCustomer } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import { DataTable, type Column } from '@/components/common/DataTable';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ContractFormData {
  contract_number: string;
  customer_id: string;
  value_per_period: string;
  periodicity_months: string;
  currency: string;
  activation_date: string;
  expiration_date: string;
  notes_internal: string;
}

const getTodayDate = () => {
  return new Date().toISOString().split('T')[0];
};

const emptyForm: ContractFormData = {
  contract_number: '',
  customer_id: '',
  value_per_period: '',
  periodicity_months: '12',
  currency: 'EUR',
  activation_date: getTodayDate(),
  expiration_date: '',
  notes_internal: '',
};

export const Contracts: React.FC = () => {
  const { t } = useTranslation(['contracts', 'common']);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState<ContractFormData>(emptyForm);
  const [customerSearch, setCustomerSearch] = useState('');

  // Calculate total value based on duration and value per period
  const calculatedTotalValue = useMemo(() => {
    if (!formData.value_per_period || !formData.activation_date || !formData.expiration_date) {
      return null;
    }
    const valuePerPeriod = parseFloat(formData.value_per_period);
    const periodicityMonths = parseInt(formData.periodicity_months) || 12;

    const startDate = new Date(formData.activation_date);
    const endDate = new Date(formData.expiration_date);

    // Calculate months between dates
    const months = (endDate.getFullYear() - startDate.getFullYear()) * 12 +
                   (endDate.getMonth() - startDate.getMonth());

    if (months <= 0) return null;

    // Number of billing periods
    const periods = Math.ceil(months / periodicityMonths);
    return valuePerPeriod * periods;
  }, [formData.value_per_period, formData.periodicity_months, formData.activation_date, formData.expiration_date]);

  const { data: contracts, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll(),
  });

  // Fetch Pennylane customers for selection
  const { data: customersData } = useQuery({
    queryKey: ['pennylane-customers', customerSearch],
    queryFn: () => pennylaneApi.getCustomers(1, 100, { search: customerSearch || undefined }),
  });

  const customers = customersData?.items || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ContractCreateRequest) => contractsApi.createContract(data),
    onSuccess: () => {
      toast({
        title: t('common:success'),
        description: t('contracts:contract_created'),
      });
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      setDialogOpen(false);
      setFormData({ ...emptyForm, activation_date: getTodayDate() });
    },
    onError: (error: any) => {
      toast({
        title: t('common:error'),
        description: error.response?.data?.detail || t('contracts:error_creating_contract'),
        variant: 'destructive',
      });
    },
  });

  const handleAdd = () => {
    setFormData({ ...emptyForm, activation_date: getTodayDate() });
    setDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.customer_id) {
      toast({
        title: t('common:error'),
        description: t('contracts:customer_required'),
        variant: 'destructive',
      });
      return;
    }

    const submitData: ContractCreateRequest = {
      contract_number: formData.contract_number || undefined,
      customer_id: formData.customer_id,
      value_per_period: formData.value_per_period ? parseFloat(formData.value_per_period) : undefined,
      periodicity_months: formData.periodicity_months ? parseInt(formData.periodicity_months) : 12,
      currency: formData.currency || 'EUR',
      activation_date: formData.activation_date || undefined,
      expiration_date: formData.expiration_date || undefined,
      notes_internal: formData.notes_internal || undefined,
    };

    createMutation.mutate(submitData);
  };

  const columns: Column<Contract>[] = [
    {
      key: 'contract_number',
      header: t('contracts:contract_number'),
    },
    {
      key: 'customer_name',
      header: t('contracts:customer_name'),
    },
    {
      key: 'status',
      header: t('contracts:status'),
      render: (contract) => <StatusBadge status={contract.status} type="contract" />,
    },
    {
      key: 'start_date',
      header: t('contracts:start_date'),
      render: (contract) => formatDate(contract.start_date),
    },
    {
      key: 'end_date',
      header: t('contracts:end_date'),
      render: (contract) => contract.end_date ? formatDate(contract.end_date) : '-',
    },
    {
      key: 'total_value',
      header: t('contracts:total_value'),
      render: (contract) => formatCurrency(contract.total_value, contract.currency),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('contracts:title')}</h1>
          <p className="text-muted-foreground">{t('contracts:description')}</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          {t('contracts:create_contract')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('contracts:title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={contracts || []} columns={columns} />
        </CardContent>
      </Card>

      {/* Create Contract Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('contracts:create_contract')}</DialogTitle>
            <DialogDescription>
              {t('contracts:create_new_contract_desc')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="customer_id">{t('common:customer')} *</Label>
                <Select
                  value={formData.customer_id}
                  onValueChange={(value) => setFormData({ ...formData, customer_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('common:select_customer')} />
                  </SelectTrigger>
                  <SelectContent>
                    <div className="px-2 py-1">
                      <Input
                        placeholder={t('pennylane:search_customers')}
                        value={customerSearch}
                        onChange={(e) => setCustomerSearch(e.target.value)}
                        className="h-8"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => e.stopPropagation()}
                      />
                    </div>
                    {customers.map((customer: PennylaneCustomer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="contract_number">{t('contracts:contract_number')}</Label>
                <Input
                  id="contract_number"
                  value={formData.contract_number}
                  onChange={(e) => setFormData({ ...formData, contract_number: e.target.value })}
                  placeholder={t('contracts:auto_generated_if_empty')}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="value_per_period">{t('contracts:value_per_period')} *</Label>
                  <Input
                    id="value_per_period"
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.value_per_period}
                    onChange={(e) => setFormData({ ...formData, value_per_period: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="periodicity_months">{t('contracts:periodicity_months_label')}</Label>
                  <Input
                    id="periodicity_months"
                    type="number"
                    min="1"
                    value={formData.periodicity_months}
                    onChange={(e) => setFormData({ ...formData, periodicity_months: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="currency">{t('contracts:currency')}</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(value) => setFormData({ ...formData, currency: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="activation_date">{t('contracts:activation_date')}</Label>
                  <Input
                    id="activation_date"
                    type="date"
                    value={formData.activation_date}
                    onChange={(e) => setFormData({ ...formData, activation_date: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="expiration_date">{t('contracts:expiration_date')}</Label>
                  <Input
                    id="expiration_date"
                    type="date"
                    value={formData.expiration_date}
                    onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
                  />
                </div>
              </div>

              {/* Calculated total value preview */}
              {calculatedTotalValue !== null && (
                <div className="rounded-md bg-muted p-3">
                  <Label className="text-sm text-muted-foreground">{t('contracts:calculated_total_value')}</Label>
                  <p className="text-lg font-semibold">
                    {formatCurrency(calculatedTotalValue, formData.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">{t('contracts:total_value_preview')}</p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="notes_internal">{t('contracts:notes')}</Label>
                <textarea
                  id="notes_internal"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  value={formData.notes_internal}
                  onChange={(e) => setFormData({ ...formData, notes_internal: e.target.value })}
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDialogOpen(false);
                  setFormData({ ...emptyForm, activation_date: getTodayDate() });
                }}
              >
                {t('contracts:cancel')}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || !formData.value_per_period || !formData.customer_id}
              >
                {t('contracts:create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
