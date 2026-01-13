import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams, Link } from 'react-router-dom';
import { pennylaneApi, contractsApi } from '@/services/api';
import { type PennylaneInvoice, type PennylaneConnection, type Contract, type ContractCreateRequest } from '@/types';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { formatCurrency, formatDate } from '@/lib/utils';
import {
  ServerDataTable,
  useServerTableState,
  type ServerColumn,
  type PaginationInfo,
} from '@/components/common/ServerDataTable';
import { FileText, ExternalLink, Search, ChevronDown, X, Link as LinkIcon, Unlink, Plus, Ban, Pencil } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

const INVOICE_STATUSES = ['draft', 'finalized', 'paid', 'overdue', 'upcoming', 'cancelled'] as const;

const getInvoiceStatusVariant = (status?: string): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  switch (status?.toLowerCase()) {
    case 'draft':
      return 'secondary';
    case 'finalized':
      return 'info';
    case 'paid':
      return 'success';
    case 'overdue':
      return 'destructive';
    case 'upcoming':
      return 'warning';
    case 'cancelled':
      return 'destructive';
    default:
      return 'outline';
  }
};

export const PennylaneInvoices: React.FC = () => {
  const { t } = useTranslation(['pennylane', 'common', 'contracts']);
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL params
  const [connectionFilter, setConnectionFilter] = useState<string>(
    searchParams.get('connection') || 'all'
  );
  const [statusFilter, setStatusFilter] = useState<string[]>(() => {
    const statusParam = searchParams.get('status');
    return statusParam ? statusParam.split(',') : [];
  });
  const [statusPopoverOpen, setStatusPopoverOpen] = useState(false);
  const [fromDate, setFromDate] = useState<string>(searchParams.get('from') || '');
  const [toDate, setToDate] = useState<string>(searchParams.get('to') || '');
  const [searchQuery, setSearchQuery] = useState<string>(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState<string>(searchParams.get('search') || '');
  const [contractFilter, setContractFilter] = useState<string>(
    searchParams.get('contract') || 'all'
  );
  const [selectedInvoice, setSelectedInvoice] = useState<PennylaneInvoice | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);
  const [showCreateContract, setShowCreateContract] = useState(false);
  const [newContractData, setNewContractData] = useState<ContractCreateRequest>({
    contract_number: '',
    customer_id: '',
    value_per_period: 0,
    periodicity_months: 12,
    currency: 'EUR',
    activation_date: new Date().toISOString().split('T')[0],
    expiration_date: '',
    notes_internal: '',
  });
  const [isCreatingContract, setIsCreatingContract] = useState(false);
  const queryClient = useQueryClient();

  const {
    page,
    pageSize,
    sort,
    sortParam,
    handleSort,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  } = useServerTableState(25);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      resetPagination();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, resetPagination]);

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (connectionFilter !== 'all') params.set('connection', connectionFilter);
    if (statusFilter.length > 0) params.set('status', statusFilter.join(','));
    if (fromDate) params.set('from', fromDate);
    if (toDate) params.set('to', toDate);
    if (debouncedSearch) params.set('search', debouncedSearch);
    if (contractFilter !== 'all') params.set('contract', contractFilter);
    setSearchParams(params, { replace: true });
  }, [connectionFilter, statusFilter, fromDate, toDate, debouncedSearch, contractFilter, setSearchParams]);

  const { data: connections } = useQuery({
    queryKey: ['pennylane-connections'],
    queryFn: () => pennylaneApi.getConnections(),
  });

  const { data: contracts } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll(),
  });

  const { data: invoicesData, isLoading, isFetching } = useQuery({
    queryKey: [
      'pennylane-invoices',
      page,
      pageSize,
      connectionFilter,
      statusFilter,
      fromDate,
      toDate,
      debouncedSearch,
      sortParam,
      contractFilter,
    ],
    queryFn: () =>
      pennylaneApi.getInvoices(page, pageSize, {
        connection_id: connectionFilter !== 'all' ? connectionFilter : undefined,
        status: statusFilter.length > 0 ? statusFilter.join(',') : undefined,
        date_from: fromDate || undefined,
        date_to: toDate || undefined,
        search: debouncedSearch || undefined,
        sort: sortParam,
        contract_id: contractFilter !== 'all' ? contractFilter : undefined,
      }),
  });

  const linkContractMutation = useMutation({
    mutationFn: ({ invoiceId, contractId, noContract = false }: { invoiceId: string; contractId: string | null; noContract?: boolean }) =>
      pennylaneApi.linkInvoiceToContract(invoiceId, contractId, noContract),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pennylane-invoices'] });
      // Update selected invoice with new contract info
      if (selectedInvoice && variables.contractId) {
        const contract = contracts?.find((c: Contract) => c.id.toString() === variables.contractId);
        setSelectedInvoice({
          ...selectedInvoice,
          contract_id: variables.contractId,
          contract_number: contract?.contract_number,
          no_contract: false,
        });
      } else if (selectedInvoice && variables.noContract) {
        setSelectedInvoice({
          ...selectedInvoice,
          contract_id: undefined,
          contract_number: undefined,
          no_contract: true,
        });
      } else if (selectedInvoice) {
        setSelectedInvoice({
          ...selectedInvoice,
          contract_id: undefined,
          contract_number: undefined,
          no_contract: false,
        });
      }
    },
  });

  const invoices = invoicesData?.items || [];
  const pagination: PaginationInfo = invoicesData?.pagination || {
    page: 1,
    page_size: pageSize,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };

  const handleConnectionChange = (value: string) => {
    setConnectionFilter(value);
    resetPagination();
  };

  const handleStatusToggle = (status: string) => {
    setStatusFilter((prev) => {
      if (prev.includes(status)) {
        return prev.filter((s) => s !== status);
      } else {
        return [...prev, status];
      }
    });
    resetPagination();
  };

  const handleClearStatuses = () => {
    setStatusFilter([]);
    resetPagination();
  };

  const handleFromDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFromDate(e.target.value);
    resetPagination();
  };

  const handleToDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setToDate(e.target.value);
    resetPagination();
  };

  const handleContractFilterChange = (value: string) => {
    setContractFilter(value);
    resetPagination();
  };

  const handleRowClick = (invoice: PennylaneInvoice) => {
    setSelectedInvoice(invoice);
    setSelectedContractId(invoice.contract_id || null);
    setIsDetailOpen(true);
  };

  const handleLinkContract = () => {
    if (selectedInvoice) {
      linkContractMutation.mutate({
        invoiceId: selectedInvoice.id,
        contractId: selectedContractId,
      });
    }
  };

  const handleUnlinkContract = () => {
    if (selectedInvoice) {
      setSelectedContractId(null);
      linkContractMutation.mutate({
        invoiceId: selectedInvoice.id,
        contractId: null,
      });
    }
  };

  const handleMarkNoContract = () => {
    if (selectedInvoice) {
      linkContractMutation.mutate({
        invoiceId: selectedInvoice.id,
        contractId: null,
        noContract: true,
      });
    }
  };

  const handleClearNoContract = () => {
    if (selectedInvoice) {
      linkContractMutation.mutate({
        invoiceId: selectedInvoice.id,
        contractId: null,
        noContract: false,
      });
    }
  };

  const handleCreateAndLinkContract = async () => {
    if (!selectedInvoice) return;

    setIsCreatingContract(true);
    try {
      const contractData: ContractCreateRequest = {
        ...newContractData,
        contract_number: newContractData.contract_number || undefined,
        expiration_date: newContractData.expiration_date || undefined,
        notes_internal: newContractData.notes_internal || undefined,
      };

      const newContract = await contractsApi.createContract(contractData);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });

      // Link the invoice to the newly created contract
      linkContractMutation.mutate({
        invoiceId: selectedInvoice.id,
        contractId: newContract.id.toString(),
      });

      // Reset form and close
      setShowCreateContract(false);
      setNewContractData({
        contract_number: '',
        customer_id: '',
        value_per_period: 0,
        periodicity_months: 12,
        currency: 'EUR',
        activation_date: new Date().toISOString().split('T')[0],
        expiration_date: '',
        notes_internal: '',
      });
    } catch (error) {
      console.error('Failed to create contract:', error);
    } finally {
      setIsCreatingContract(false);
    }
  };

  const renderCustomerLink = (invoice: PennylaneInvoice) => {
    if (invoice.customer_id && invoice.customer_name) {
      return (
        <Link
          to={`/pennylane/customers?pennylane_id=${encodeURIComponent(invoice.customer_id)}`}
          className="text-blue-600 hover:text-blue-800 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {invoice.customer_name}
        </Link>
      );
    }
    return invoice.customer_name || '-';
  };

  const columns: ServerColumn<PennylaneInvoice>[] = [
    {
      key: 'invoice_number',
      header: t('invoice_number', 'Invoice #'),
      sortable: true,
      render: (invoice) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{invoice.invoice_number || '-'}</span>
        </div>
      ),
    },
    {
      key: 'customer_name',
      header: t('common:customer_name', 'Customer'),
      sortable: true,
      render: renderCustomerLink,
    },
    {
      key: 'status',
      header: t('common:status', 'Status'),
      sortable: true,
      render: (invoice) => (
        <Badge variant={getInvoiceStatusVariant(invoice.status)}>
          {invoice.status ? t(`status.${invoice.status}`, invoice.status) : 'unknown'}
        </Badge>
      ),
    },
    {
      key: 'amount',
      header: t('amount', 'Amount'),
      sortable: true,
      className: 'text-right',
      render: (invoice) =>
        invoice.amount != null ? formatCurrency(invoice.amount, invoice.currency) : '-',
    },
    {
      key: 'currency',
      header: t('currency', 'Currency'),
      render: (invoice) => invoice.currency || '-',
    },
    {
      key: 'issue_date',
      header: t('issue_date', 'Issue Date'),
      sortable: true,
      render: (invoice) => (invoice.issue_date ? formatDate(invoice.issue_date) : '-'),
    },
    {
      key: 'due_date',
      header: t('due_date', 'Due Date'),
      sortable: true,
      render: (invoice) => (invoice.due_date ? formatDate(invoice.due_date) : '-'),
    },
    {
      key: 'contract_number',
      header: t('contracts:contract'),
      render: (invoice) =>
        invoice.contract_id && invoice.contract_number ? (
          <Link
            to={`/contracts?id=${invoice.contract_id}`}
            className="text-blue-600 hover:text-blue-800 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {invoice.contract_number}
          </Link>
        ) : invoice.no_contract ? (
          <Badge variant="secondary" className="text-muted-foreground">
            {t('contracts:no_contract')}
          </Badge>
        ) : (
          '-'
        ),
    },
    {
      key: 'connection_name',
      header: t('connection', 'Connection'),
      render: (invoice) => invoice.connection_name || '-',
    },
    {
      key: 'pdf_url',
      header: t('pdf', 'PDF'),
      render: (invoice) =>
        invoice.pdf_url ? (
          <a
            href={invoice.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-4 w-4" />
            {t('view_pdf', 'View')}
          </a>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('invoices_title', 'Pennylane Invoices')}</h1>
          <p className="text-muted-foreground">
            {t('invoices_description', 'View synced invoices from Pennylane')}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">{t('filters', 'Filters')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="w-64 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('search_invoices', 'Search by number or customer...')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="w-48">
              <Select value={connectionFilter} onValueChange={handleConnectionChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('all_connections', 'All Connections')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('all_connections', 'All Connections')}</SelectItem>
                  {connections?.map((conn: PennylaneConnection) => (
                    <SelectItem key={conn.id} value={conn.id}>
                      {conn.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-48">
              <Popover open={statusPopoverOpen} onOpenChange={setStatusPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-normal"
                  >
                    <span className="truncate">
                      {statusFilter.length === 0
                        ? t('all_statuses', 'All Statuses')
                        : statusFilter.length === 1
                          ? t(`status.${statusFilter[0]}`, statusFilter[0])
                          : t('selected_count', '{{count}} selected', { count: statusFilter.length })}
                    </span>
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-48 p-2" align="start">
                  <div className="space-y-2">
                    {statusFilter.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start text-muted-foreground"
                        onClick={handleClearStatuses}
                      >
                        <X className="mr-2 h-4 w-4" />
                        {t('clear_selection', 'Clear')}
                      </Button>
                    )}
                    {INVOICE_STATUSES.map((status) => (
                      <div
                        key={status}
                        className="flex items-center space-x-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-2 py-1"
                        onClick={() => handleStatusToggle(status)}
                      >
                        <Checkbox
                          checked={statusFilter.includes(status)}
                          onCheckedChange={() => handleStatusToggle(status)}
                        />
                        <span className="text-sm">
                          {t(`status.${status}`, status)}
                        </span>
                      </div>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            </div>
            <div className="w-40">
              <Input
                type="date"
                placeholder={t('from_date', 'From Date')}
                value={fromDate}
                onChange={handleFromDateChange}
              />
            </div>
            <div className="w-40">
              <Input
                type="date"
                placeholder={t('to_date', 'To Date')}
                value={toDate}
                onChange={handleToDateChange}
              />
            </div>
            <div className="w-48">
              <Select value={contractFilter} onValueChange={handleContractFilterChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('pennylane:all_contracts')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('pennylane:all_contracts')}</SelectItem>
                  <SelectItem value="linked">{t('contracts:linked')}</SelectItem>
                  <SelectItem value="no_contract">{t('contracts:no_contract')}</SelectItem>
                  <SelectItem value="unlinked">{t('contracts:unlinked')}</SelectItem>
                  {contracts?.map((contract: Contract) => (
                    <SelectItem key={contract.id} value={contract.id.toString()}>
                      {contract.contract_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">
            {t('invoices_list', 'Invoices')} ({pagination.total_items})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ServerDataTable
            data={invoices}
            columns={columns}
            pagination={pagination}
            sort={sort}
            isLoading={isLoading || isFetching}
            onRowClick={handleRowClick}
            onSort={handleSort}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </CardContent>
      </Card>

      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('invoice_details', 'Invoice Details')}</DialogTitle>
          </DialogHeader>
          {selectedInvoice && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('invoice_number', 'Invoice #')}
                  </label>
                  <p className="text-sm font-medium">{selectedInvoice.invoice_number || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('common:customer_name', 'Customer')}
                  </label>
                  <p className="text-sm">
                    {selectedInvoice.customer_id && selectedInvoice.customer_name ? (
                      <Link
                        to={`/pennylane/customers?pennylane_id=${encodeURIComponent(selectedInvoice.customer_id)}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {selectedInvoice.customer_name}
                      </Link>
                    ) : (
                      selectedInvoice.customer_name || '-'
                    )}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('common:status', 'Status')}
                  </label>
                  <p className="text-sm">
                    <Badge variant={getInvoiceStatusVariant(selectedInvoice.status)}>
                      {selectedInvoice.status ? t(`status.${selectedInvoice.status}`, selectedInvoice.status) : 'unknown'}
                    </Badge>
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('amount', 'Amount')}
                  </label>
                  <p className="text-sm font-medium">
                    {selectedInvoice.amount != null
                      ? formatCurrency(selectedInvoice.amount, selectedInvoice.currency)
                      : '-'}
                    {selectedInvoice.currency && ` (${selectedInvoice.currency})`}
                  </p>
                </div>
              </div>
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">{t('dates', 'Dates')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('issue_date', 'Issue Date')}
                    </label>
                    <p className="text-sm">
                      {selectedInvoice.issue_date ? formatDate(selectedInvoice.issue_date) : '-'}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('due_date', 'Due Date')}
                    </label>
                    <p className="text-sm">
                      {selectedInvoice.due_date ? formatDate(selectedInvoice.due_date) : '-'}
                    </p>
                  </div>
                  {selectedInvoice.paid_date && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('paid_date', 'Paid Date')}
                      </label>
                      <p className="text-sm">{formatDate(selectedInvoice.paid_date)}</p>
                    </div>
                  )}
                </div>
              </div>
              <div className="border-t pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('connection', 'Connection')}
                    </label>
                    <p className="text-sm">{selectedInvoice.connection_name || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('pennylane_id', 'Pennylane ID')}
                    </label>
                    <p className="text-sm font-mono text-xs">{selectedInvoice.pennylane_id}</p>
                  </div>
                  {selectedInvoice.pdf_url && (
                    <div className="col-span-2">
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('pdf', 'PDF')}
                      </label>
                      <p className="text-sm">
                        <a
                          href={selectedInvoice.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          <ExternalLink className="h-4 w-4" />
                          {t('view_pdf', 'View PDF')}
                        </a>
                      </p>
                    </div>
                  )}
                </div>
              </div>
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">{t('contracts:contract_linking')}</h4>
                <div className="space-y-3">
                  {selectedInvoice.no_contract === true ? (
                    // Show "No contract" state
                    <div className="flex items-center justify-between">
                      <div>
                        <Badge variant="secondary" className="text-muted-foreground">
                          <Ban className="h-3 w-3 mr-1" />
                          {t('contracts:explicitly_no_contract')}
                        </Badge>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleClearNoContract}
                        disabled={linkContractMutation.isPending}
                      >
                        <Pencil className="h-4 w-4 mr-2" />
                        {t('contracts:edit')}
                      </Button>
                    </div>
                  ) : selectedInvoice.contract_id && selectedInvoice.contract_number ? (
                    // Show linked contract
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          {t('contracts:linked_contract')}
                        </label>
                        <p className="text-sm">
                          <Link
                            to={`/contracts?id=${selectedInvoice.contract_id}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline"
                          >
                            {selectedInvoice.contract_number}
                          </Link>
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleUnlinkContract}
                        disabled={linkContractMutation.isPending}
                      >
                        <Unlink className="h-4 w-4 mr-2" />
                        {t('contracts:unlink')}
                      </Button>
                    </div>
                  ) : (
                    // Show linking options
                    <div className="space-y-4">
                      {/* Existing contract selection */}
                      <div className="flex items-end gap-3">
                        <div className="flex-1">
                          <label className="text-sm font-medium text-muted-foreground mb-1 block">
                            {t('contracts:select_contract')}
                          </label>
                          <Select
                            value={selectedContractId || ''}
                            onValueChange={(value) => setSelectedContractId(value || null)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder={t('contracts:select_contract_placeholder')} />
                            </SelectTrigger>
                            <SelectContent>
                              {contracts?.map((contract: Contract) => (
                                <SelectItem key={contract.id} value={contract.id.toString()}>
                                  {contract.contract_number} - {contract.customer_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <Button
                          onClick={handleLinkContract}
                          disabled={!selectedContractId || linkContractMutation.isPending}
                        >
                          <LinkIcon className="h-4 w-4 mr-2" />
                          {t('contracts:link')}
                        </Button>
                      </div>

                      {/* Action buttons */}
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            if (!showCreateContract && selectedInvoice?.customer_id) {
                              // Pre-fill customer from invoice when opening the form
                              setNewContractData(prev => ({
                                ...prev,
                                customer_id: selectedInvoice.customer_id || '',
                              }));
                            }
                            setShowCreateContract(!showCreateContract);
                          }}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          {t('contracts:create_new_contract')}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleMarkNoContract}
                          disabled={linkContractMutation.isPending}
                        >
                          <Ban className="h-4 w-4 mr-2" />
                          {t('contracts:mark_as_no_contract')}
                        </Button>
                      </div>

                      {/* Inline contract creation form */}
                      {showCreateContract && (
                        <div className="border rounded-md p-4 space-y-4 bg-muted/50">
                          <h5 className="text-sm font-medium">{t('contracts:new_contract')}</h5>
                          <div className="grid grid-cols-2 gap-3">
                            {/* Customer field - read-only when pre-filled from invoice */}
                            <div className="col-span-2">
                              <Label htmlFor="customer" className="text-xs">
                                {t('common:customer')}
                              </Label>
                              <Input
                                id="customer"
                                value={selectedInvoice?.customer_name || ''}
                                disabled
                                className="mt-1 bg-muted"
                              />
                            </div>
                            <div>
                              <Label htmlFor="contract_number" className="text-xs">
                                {t('contracts:contract_number_optional')}
                              </Label>
                              <Input
                                id="contract_number"
                                value={newContractData.contract_number || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, contract_number: e.target.value })}
                                placeholder={t('contracts:auto_generated')}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <Label htmlFor="value_per_period" className="text-xs">
                                {t('contracts:value_per_period')} *
                              </Label>
                              <Input
                                id="value_per_period"
                                type="number"
                                step="0.01"
                                min="0"
                                value={newContractData.value_per_period || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, value_per_period: parseFloat(e.target.value) || 0 })}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <Label htmlFor="periodicity_months" className="text-xs">
                                {t('contracts:periodicity_months_label')}
                              </Label>
                              <Input
                                id="periodicity_months"
                                type="number"
                                min="1"
                                value={newContractData.periodicity_months || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, periodicity_months: parseInt(e.target.value) || 1 })}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <Label htmlFor="currency" className="text-xs">
                                {t('contracts:currency')}
                              </Label>
                              <Select
                                value={newContractData.currency || 'EUR'}
                                onValueChange={(value) => setNewContractData({ ...newContractData, currency: value })}
                              >
                                <SelectTrigger className="mt-1">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="EUR">EUR</SelectItem>
                                  <SelectItem value="USD">USD</SelectItem>
                                  <SelectItem value="GBP">GBP</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div>
                              <Label htmlFor="activation_date" className="text-xs">
                                {t('contracts:activation_date')}
                              </Label>
                              <Input
                                id="activation_date"
                                type="date"
                                value={newContractData.activation_date || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, activation_date: e.target.value })}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <Label htmlFor="expiration_date" className="text-xs">
                                {t('contracts:expiration_date_optional')}
                              </Label>
                              <Input
                                id="expiration_date"
                                type="date"
                                value={newContractData.expiration_date || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, expiration_date: e.target.value })}
                                className="mt-1"
                              />
                            </div>
                            <div className="col-span-2">
                              <Label htmlFor="notes" className="text-xs">
                                {t('contracts:notes_optional')}
                              </Label>
                              <Textarea
                                id="notes"
                                value={newContractData.notes_internal || ''}
                                onChange={(e) => setNewContractData({ ...newContractData, notes_internal: e.target.value })}
                                className="mt-1"
                                rows={2}
                              />
                            </div>
                          </div>
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setShowCreateContract(false)}
                            >
                              {t('contracts:cancel')}
                            </Button>
                            <Button
                              size="sm"
                              onClick={handleCreateAndLinkContract}
                              disabled={isCreatingContract || !newContractData.value_per_period}
                            >
                              {isCreatingContract ? t('contracts:creating') : t('contracts:create_and_link')}
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
