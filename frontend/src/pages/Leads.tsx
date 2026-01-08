import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { leadsApi } from '@/services/api';
import { type Lead, LeadStatus } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Plus, List, LayoutGrid } from 'lucide-react';
import { DataTable, type Column } from '@/components/common/DataTable';
import { LeadDialog } from '@/components/leads/LeadDialog';

export const Leads: React.FC = () => {
  const { t } = useTranslation(['leads', 'common']);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>('list');

  const { data: leads, isLoading } = useQuery({
    queryKey: ['leads'],
    queryFn: () => leadsApi.getAll(),
  });

  const columns: Column<Lead>[] = [
    {
      key: 'customer_name',
      header: t('common:customer_name'),
    },
    {
      key: 'customer_email',
      header: t('common:customer_email'),
    },
    {
      key: 'customer_company',
      header: t('common:company'),
      render: (lead) => lead.customer_company || '-',
    },
    {
      key: 'status',
      header: t('common:status'),
      render: (lead) => <StatusBadge status={lead.status} type="lead" />,
    },
    {
      key: 'estimated_value',
      header: t('estimated_value'),
      render: (lead) =>
        lead.estimated_value ? formatCurrency(lead.estimated_value) : '-',
    },
    {
      key: 'expected_close_date',
      header: t('expected_close_date'),
      render: (lead) =>
        lead.expected_close_date ? formatDate(lead.expected_close_date) : '-',
    },
    {
      key: 'created_at',
      header: t('common:created_at'),
      render: (lead) => formatDate(lead.created_at),
    },
  ];

  const statuses: LeadStatus[] = [
    LeadStatus.NEW,
    LeadStatus.CONTACTED,
    LeadStatus.QUALIFIED,
    LeadStatus.PROPOSAL,
    LeadStatus.NEGOTIATION,
    LeadStatus.WON,
    LeadStatus.LOST,
  ];

  const groupedLeads = leads?.reduce((acc, lead) => {
    if (!acc[lead.status]) {
      acc[lead.status] = [];
    }
    acc[lead.status].push(lead);
    return acc;
  }, {} as Record<LeadStatus, Lead[]>);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground">{t('common:manage_sales_pipeline')}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'kanban' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setViewMode('kanban')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => {
              setSelectedLead(null);
              setIsDialogOpen(true);
            }}
          >
            <Plus className="h-4 w-4 mr-2" />
            {t('add_lead')}
          </Button>
        </div>
      </div>

      {viewMode === 'list' ? (
        <Card>
          <CardHeader>
            <CardTitle>{t('title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              data={leads || []}
              columns={columns}
              onRowClick={(lead) => {
                setSelectedLead(lead);
                setIsDialogOpen(true);
              }}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {statuses.map((status) => (
            <Card key={status} className="flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  <StatusBadge status={status} type="lead" />
                  <span className="ml-2 text-muted-foreground">
                    ({groupedLeads?.[status]?.length || 0})
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-2">
                {groupedLeads?.[status]?.map((lead) => (
                  <Card
                    key={lead.id}
                    className="cursor-pointer hover:shadow-md transition-shadow p-3"
                    onClick={() => {
                      setSelectedLead(lead);
                      setIsDialogOpen(true);
                    }}
                  >
                    <div className="font-medium text-sm">{lead.customer_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {lead.customer_email}
                    </div>
                    {lead.estimated_value && (
                      <div className="text-xs font-medium mt-1">
                        {formatCurrency(lead.estimated_value)}
                      </div>
                    )}
                  </Card>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <LeadDialog
        lead={selectedLead}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
};
