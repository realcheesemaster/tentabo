import React from 'react';
import { Badge } from '@/components/ui/badge';
import { LeadStatus, OrderStatus, ContractStatus } from '@/types';
import { useTranslation } from 'react-i18next';

interface StatusBadgeProps {
  status: LeadStatus | OrderStatus | ContractStatus | string;
  type: 'lead' | 'order' | 'contract';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type }) => {
  const { t } = useTranslation([type + 's', 'orders', 'leads']);

  const getVariant = (status: string) => {
    switch (status) {
      case 'new':
      case 'draft':
        return 'secondary';
      case 'contacted':
      case 'pending':
        return 'info';
      case 'qualified':
      case 'processing':
        return 'warning';
      case 'proposal':
      case 'confirmed':
      case 'active':
        return 'info';
      case 'negotiation':
        return 'warning';
      case 'won':
      case 'delivered':
        return 'success';
      case 'lost':
      case 'cancelled':
      case 'terminated':
        return 'destructive';
      case 'expired':
        return 'secondary';
      default:
        return 'default';
    }
  };

  return (
    <Badge variant={getVariant(status)}>
      {t(`status.${status}`, { defaultValue: status })}
    </Badge>
  );
};
