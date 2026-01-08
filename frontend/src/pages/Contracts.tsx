import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { contractsApi } from '@/services/api';
import { type Contract } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import { DataTable, type Column } from '@/components/common/DataTable';

export const Contracts: React.FC = () => {
  const { t } = useTranslation('common');

  const { data: contracts, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll(),
  });

  const columns: Column<Contract>[] = [
    {
      key: 'contract_number',
      header: t('contract_number'),
    },
    {
      key: 'customer_name',
      header: t('customer_name'),
    },
    {
      key: 'status',
      header: t('status'),
      render: (contract) => <StatusBadge status={contract.status} type="contract" />,
    },
    {
      key: 'start_date',
      header: t('start_date'),
      render: (contract) => formatDate(contract.start_date),
    },
    {
      key: 'end_date',
      header: t('end_date'),
      render: (contract) => contract.end_date ? formatDate(contract.end_date) : '-',
    },
    {
      key: 'total_value',
      header: t('total_value'),
      render: (contract) => formatCurrency(contract.total_value, contract.currency),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('contracts')}</h1>
        <p className="text-muted-foreground">{t('manage_customer_contracts')}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('contracts')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={contracts || []} columns={columns} />
        </CardContent>
      </Card>
    </div>
  );
};
