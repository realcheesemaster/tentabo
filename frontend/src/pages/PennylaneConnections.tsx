import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { pennylaneApi } from '@/services/api';
import { type PennylaneConnection, type PennylaneConnectionCreate, type PennylaneConnectionUpdate } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';
import { Plus, Edit, Trash2, TestTube2, RefreshCw, Check, X, Users, FileText, FileCheck, CalendarClock } from 'lucide-react';
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
import { Switch } from '@/components/ui/switch';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ConnectionFormData {
  name: string;
  api_token: string;
  sync_customers: boolean;
  sync_invoices: boolean;
  sync_quotes: boolean;
  sync_subscriptions: boolean;
}

const emptyForm: ConnectionFormData = {
  name: '',
  api_token: '',
  sync_customers: true,
  sync_invoices: true,
  sync_quotes: true,
  sync_subscriptions: true,
};

export const PennylaneConnections: React.FC = () => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<PennylaneConnection | null>(null);
  const [deletingConnection, setDeletingConnection] = useState<PennylaneConnection | null>(null);
  const [formData, setFormData] = useState<ConnectionFormData>(emptyForm);
  const [syncingConnectionId, setSyncingConnectionId] = useState<string | null>(null);

  const { data: connections, isLoading } = useQuery({
    queryKey: ['pennylane-connections'],
    queryFn: () => pennylaneApi.getConnections(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: PennylaneConnectionCreate) => pennylaneApi.createConnection(data),
    onSuccess: () => {
      toast({
        title: t('success', 'Success'),
        description: t('pennylane_connection_created', 'Pennylane connection created successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['pennylane-connections'] });
      setDialogOpen(false);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error', 'Error'),
        description: error.response?.data?.detail || t('failed_to_create_connection', 'Failed to create connection'),
        variant: 'destructive',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PennylaneConnectionUpdate }) =>
      pennylaneApi.updateConnection(id, data),
    onSuccess: () => {
      toast({
        title: t('success', 'Success'),
        description: t('pennylane_connection_updated', 'Pennylane connection updated successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['pennylane-connections'] });
      setDialogOpen(false);
      setEditingConnection(null);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error', 'Error'),
        description: error.response?.data?.detail || t('failed_to_update_connection', 'Failed to update connection'),
        variant: 'destructive',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => pennylaneApi.deleteConnection(id),
    onSuccess: () => {
      toast({
        title: t('success', 'Success'),
        description: t('pennylane_connection_deleted', 'Pennylane connection deleted successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['pennylane-connections'] });
      setDeleteDialogOpen(false);
      setDeletingConnection(null);
    },
    onError: (error: any) => {
      toast({
        title: t('error', 'Error'),
        description: error.response?.data?.detail || t('failed_to_delete_connection', 'Failed to delete connection'),
        variant: 'destructive',
      });
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: (id: string) => pennylaneApi.testConnection(id),
    onSuccess: (result) => {
      if (result.success) {
        toast({
          title: t('connection_test_success', 'Connection Test Successful'),
          description: result.company_name
            ? t('connected_to_company', 'Connected to {{company}}', { company: result.company_name })
            : t('connection_working', 'Connection is working properly'),
        });
        queryClient.invalidateQueries({ queryKey: ['pennylane-connections'] });
      } else {
        toast({
          title: t('connection_test_failed', 'Connection Test Failed'),
          description: result.error || t('unknown_error', 'Unknown error'),
          variant: 'destructive',
        });
      }
    },
    onError: (error: any) => {
      toast({
        title: t('connection_test_failed', 'Connection Test Failed'),
        description: error.response?.data?.detail || t('failed_to_test_connection', 'Failed to test connection'),
        variant: 'destructive',
      });
    },
  });

  // Sync connection mutation
  const syncMutation = useMutation({
    mutationFn: (id: string) => pennylaneApi.syncConnection(id),
    onMutate: (id) => {
      setSyncingConnectionId(id);
    },
    onSuccess: (result) => {
      setSyncingConnectionId(null);
      const totalItems = result.results.reduce((sum, r) => sum + r.total_fetched, 0);

      if (result.overall_status === 'success') {
        toast({
          title: t('sync_complete', 'Sync Complete'),
          description: t('synced_items', 'Synced {{count}} items from Pennylane', { count: totalItems }),
        });
      } else if (result.overall_status === 'partial') {
        toast({
          title: t('sync_partial', 'Sync Partially Complete'),
          description: t('synced_with_errors', 'Synced {{count}} items with some errors', { count: totalItems }),
          variant: 'destructive',
        });
      } else {
        toast({
          title: t('sync_failed', 'Sync Failed'),
          description: result.results.find(r => r.errors.length > 0)?.errors[0] || t('unknown_error', 'Unknown error'),
          variant: 'destructive',
        });
      }
      queryClient.invalidateQueries({ queryKey: ['pennylane-connections'] });
    },
    onError: (error: any) => {
      setSyncingConnectionId(null);
      toast({
        title: t('sync_failed', 'Sync Failed'),
        description: error.response?.data?.detail || t('failed_to_sync', 'Failed to sync connection'),
        variant: 'destructive',
      });
    },
  });

  const handleAdd = () => {
    setEditingConnection(null);
    setFormData(emptyForm);
    setDialogOpen(true);
  };

  const handleEdit = (connection: PennylaneConnection) => {
    setEditingConnection(connection);
    setFormData({
      name: connection.name,
      api_token: '', // Token is not pre-filled for security
      sync_customers: connection.sync_customers,
      sync_invoices: connection.sync_invoices,
      sync_quotes: connection.sync_quotes,
      sync_subscriptions: connection.sync_subscriptions,
    });
    setDialogOpen(true);
  };

  const handleDelete = (connection: PennylaneConnection) => {
    setDeletingConnection(connection);
    setDeleteDialogOpen(true);
  };

  const handleTest = (connection: PennylaneConnection) => {
    testMutation.mutate(connection.id);
  };

  const handleSync = (connection: PennylaneConnection) => {
    syncMutation.mutate(connection.id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.name || (!editingConnection && !formData.api_token)) {
      toast({
        title: t('error', 'Error'),
        description: t('please_fill_required_fields', 'Please fill in all required fields'),
        variant: 'destructive',
      });
      return;
    }

    if (editingConnection) {
      const updateData: PennylaneConnectionUpdate = {
        name: formData.name,
        sync_customers: formData.sync_customers,
        sync_invoices: formData.sync_invoices,
        sync_quotes: formData.sync_quotes,
        sync_subscriptions: formData.sync_subscriptions,
      };
      // Only include token if it was changed
      if (formData.api_token) {
        updateData.api_token = formData.api_token;
      }
      updateMutation.mutate({ id: editingConnection.id, data: updateData });
    } else {
      createMutation.mutate({
        name: formData.name,
        api_token: formData.api_token,
        sync_customers: formData.sync_customers,
        sync_invoices: formData.sync_invoices,
        sync_quotes: formData.sync_quotes,
        sync_subscriptions: formData.sync_subscriptions,
      });
    }
  };

  const getSyncStatusBadge = (status?: 'success' | 'partial' | 'failed') => {
    if (!status) return null;

    const variants: Record<string, 'success' | 'warning' | 'destructive'> = {
      success: 'success',
      partial: 'warning',
      failed: 'destructive',
    };

    const labels: Record<string, string> = {
      success: t('sync_success', 'Success'),
      partial: t('sync_partial_status', 'Partial'),
      failed: t('sync_failed_status', 'Failed'),
    };

    return (
      <Badge variant={variants[status] || 'secondary'}>
        {labels[status] || status}
      </Badge>
    );
  };

  const SyncToggle = ({ enabled, icon: Icon, label }: { enabled: boolean; icon: React.ElementType; label: string }) => (
    <div className="flex items-center gap-1" title={label}>
      <Icon className={`h-4 w-4 ${enabled ? 'text-primary' : 'text-muted-foreground'}`} />
      {enabled ? (
        <Check className="h-3 w-3 text-green-500" />
      ) : (
        <X className="h-3 w-3 text-muted-foreground" />
      )}
    </div>
  );

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('pennylane_connections', 'Pennylane Connections')}</h1>
          <p className="text-muted-foreground">{t('manage_pennylane_api_connections', 'Manage your Pennylane API connections')}</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          {t('add_connection', 'Add Connection')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('connections', 'Connections')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {connections?.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                {t('no_connections', 'No connections configured. Add your first Pennylane connection to get started.')}
              </div>
            )}
            {connections?.map((connection) => (
              <div
                key={connection.id}
                className="flex items-start justify-between border rounded-lg p-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className="font-medium text-lg">{connection.name}</div>
                    <Badge variant={connection.is_active ? 'success' : 'secondary'}>
                      {connection.is_active ? t('active', 'Active') : t('inactive', 'Inactive')}
                    </Badge>
                  </div>

                  {connection.company_name && (
                    <div className="text-sm text-muted-foreground">
                      {t('company', 'Company')}: {connection.company_name}
                    </div>
                  )}

                  <div className="text-sm text-muted-foreground">
                    {t('api_token', 'API Token')}: <code className="bg-muted px-1 rounded">{connection.masked_token}</code>
                  </div>

                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-muted-foreground">{t('sync_options', 'Sync')}:</span>
                    <SyncToggle enabled={connection.sync_customers} icon={Users} label={t('customers', 'Customers')} />
                    <SyncToggle enabled={connection.sync_invoices} icon={FileText} label={t('invoices', 'Invoices')} />
                    <SyncToggle enabled={connection.sync_quotes} icon={FileCheck} label={t('quotes', 'Quotes')} />
                    <SyncToggle enabled={connection.sync_subscriptions} icon={CalendarClock} label={t('subscriptions', 'Subscriptions')} />
                  </div>

                  {connection.last_sync_at && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">{t('last_sync', 'Last sync')}:</span>
                      <span>{formatDate(connection.last_sync_at)}</span>
                      {getSyncStatusBadge(connection.last_sync_status)}
                      {connection.last_sync_error && (
                        <span className="text-destructive text-xs" title={connection.last_sync_error}>
                          ({connection.last_sync_error.substring(0, 50)}{connection.last_sync_error.length > 50 ? '...' : ''})
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTest(connection)}
                    disabled={testMutation.isPending}
                  >
                    <TestTube2 className="h-4 w-4 mr-1" />
                    {t('test', 'Test')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSync(connection)}
                    disabled={syncingConnectionId === connection.id}
                  >
                    <RefreshCw className={`h-4 w-4 mr-1 ${syncingConnectionId === connection.id ? 'animate-spin' : ''}`} />
                    {t('sync_now', 'Sync Now')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleEdit(connection)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDelete(connection)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Connection Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingConnection ? t('edit_connection', 'Edit Connection') : t('add_connection', 'Add Connection')}
            </DialogTitle>
            <DialogDescription>
              {editingConnection
                ? t('update_connection_settings', 'Update your Pennylane connection settings')
                : t('create_new_connection', 'Create a new Pennylane API connection')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">
                  {t('name', 'Name')} <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('connection_name_placeholder', 'e.g., My Company Pennylane')}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="api_token">
                  {t('api_token', 'API Token')} {!editingConnection && <span className="text-destructive">*</span>}
                </Label>
                <Input
                  id="api_token"
                  type="password"
                  value={formData.api_token}
                  onChange={(e) => setFormData({ ...formData, api_token: e.target.value })}
                  placeholder={editingConnection ? t('leave_blank_to_keep', 'Leave blank to keep current token') : t('enter_api_token', 'Enter your Pennylane API token')}
                  required={!editingConnection}
                />
                {editingConnection && (
                  <p className="text-xs text-muted-foreground">
                    {t('current_token', 'Current token')}: {editingConnection.masked_token}
                  </p>
                )}
              </div>

              <div className="space-y-3">
                <Label>{t('sync_settings', 'Sync Settings')}</Label>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    <Label htmlFor="sync_customers" className="font-normal">{t('sync_customers', 'Sync Customers')}</Label>
                  </div>
                  <Switch
                    id="sync_customers"
                    checked={formData.sync_customers}
                    onCheckedChange={(checked) => setFormData({ ...formData, sync_customers: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    <Label htmlFor="sync_invoices" className="font-normal">{t('sync_invoices', 'Sync Invoices')}</Label>
                  </div>
                  <Switch
                    id="sync_invoices"
                    checked={formData.sync_invoices}
                    onCheckedChange={(checked) => setFormData({ ...formData, sync_invoices: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-4 w-4" />
                    <Label htmlFor="sync_quotes" className="font-normal">{t('sync_quotes', 'Sync Quotes')}</Label>
                  </div>
                  <Switch
                    id="sync_quotes"
                    checked={formData.sync_quotes}
                    onCheckedChange={(checked) => setFormData({ ...formData, sync_quotes: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CalendarClock className="h-4 w-4" />
                    <Label htmlFor="sync_subscriptions" className="font-normal">{t('sync_subscriptions', 'Sync Subscriptions')}</Label>
                  </div>
                  <Switch
                    id="sync_subscriptions"
                    checked={formData.sync_subscriptions}
                    onCheckedChange={(checked) => setFormData({ ...formData, sync_subscriptions: checked })}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDialogOpen(false);
                  setEditingConnection(null);
                  setFormData(emptyForm);
                }}
              >
                {t('cancel', 'Cancel')}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editingConnection ? t('update', 'Update') : t('create', 'Create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirm_deletion', 'Confirm Deletion')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('are_you_sure_delete_connection', 'Are you sure you want to delete the connection "{{name}}"? This will also delete all synced data from this connection.', { name: deletingConnection?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel', 'Cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingConnection && deleteMutation.mutate(deletingConnection.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('delete', 'Delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
