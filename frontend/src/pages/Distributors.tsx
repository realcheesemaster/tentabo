import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { distributorsApi } from '@/services/api';
import { type Distributor } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';
import { DataTable, type Column } from '@/components/common/DataTable';
import { Plus, Edit, Trash2 } from 'lucide-react';
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

interface DistributorFormData {
  name: string;
  legal_name: string;
  registration_number: string;
  email: string;
  phone: string;
  website: string;
  address_line1: string;
  address_line2: string;
  city: string;
  postal_code: string;
  country: string;
  is_active: boolean;
  notes: string;
}

const emptyForm: DistributorFormData = {
  name: '',
  legal_name: '',
  registration_number: '',
  email: '',
  phone: '',
  website: '',
  address_line1: '',
  address_line2: '',
  city: '',
  postal_code: '',
  country: 'France',
  is_active: true,
  notes: '',
};

export const Distributors: React.FC = () => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingDistributor, setEditingDistributor] = useState<Distributor | null>(null);
  const [deletingDistributor, setDeletingDistributor] = useState<Distributor | null>(null);
  const [formData, setFormData] = useState<DistributorFormData>(emptyForm);

  const { data: distributors, isLoading } = useQuery({
    queryKey: ['distributors'],
    queryFn: () => distributorsApi.getAll(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: Partial<Distributor>) => distributorsApi.create(data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('distributor_created_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['distributors'] });
      setDialogOpen(false);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_create_distributor'),
        variant: 'destructive',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Distributor> }) =>
      distributorsApi.update(id, data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('distributor_updated_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['distributors'] });
      setDialogOpen(false);
      setEditingDistributor(null);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_update_distributor'),
        variant: 'destructive',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => distributorsApi.delete(id),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('distributor_deleted_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['distributors'] });
      setDeleteDialogOpen(false);
      setDeletingDistributor(null);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_delete_distributor'),
        variant: 'destructive',
      });
    },
  });

  const handleAdd = () => {
    setEditingDistributor(null);
    setFormData(emptyForm);
    setDialogOpen(true);
  };

  const handleEdit = (distributor: Distributor) => {
    setEditingDistributor(distributor);
    setFormData({
      name: distributor.name || '',
      legal_name: distributor.legal_name || '',
      registration_number: distributor.registration_number || '',
      email: distributor.email || '',
      phone: distributor.phone || '',
      website: distributor.website || '',
      address_line1: distributor.address_line1 || '',
      address_line2: distributor.address_line2 || '',
      city: distributor.city || '',
      postal_code: distributor.postal_code || '',
      country: distributor.country || 'France',
      is_active: distributor.is_active,
      notes: distributor.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = (distributor: Distributor) => {
    setDeletingDistributor(distributor);
    setDeleteDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!formData.name || !formData.email) {
      toast({
        title: t('error'),
        description: t('please_fill_required_fields'),
        variant: 'destructive',
      });
      return;
    }

    const submitData = {
      ...formData,
      // Convert empty strings to undefined for optional fields
      legal_name: formData.legal_name || undefined,
      registration_number: formData.registration_number || undefined,
      phone: formData.phone || undefined,
      website: formData.website || undefined,
      address_line1: formData.address_line1 || undefined,
      address_line2: formData.address_line2 || undefined,
      city: formData.city || undefined,
      postal_code: formData.postal_code || undefined,
      notes: formData.notes || undefined,
    };

    if (editingDistributor) {
      updateMutation.mutate({ id: editingDistributor.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const columns: Column<Distributor>[] = [
    {
      key: 'name',
      header: t('name'),
    },
    {
      key: 'email',
      header: t('email'),
      render: (distributor) => distributor.email || '-',
    },
    {
      key: 'phone',
      header: t('phone'),
      render: (distributor) => distributor.phone || '-',
    },
    {
      key: 'city',
      header: t('city'),
      render: (distributor) => distributor.city || '-',
    },
    {
      key: 'country',
      header: t('country'),
      render: (distributor) => distributor.country || '-',
    },
    {
      key: 'is_active',
      header: t('status'),
      render: (distributor) => (
        <Badge variant={distributor.is_active ? 'success' : 'secondary'}>
          {distributor.is_active ? t('active') : t('inactive')}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: t('created_at'),
      render: (distributor) => formatDate(distributor.created_at),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (distributor) => (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleEdit(distributor)}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleDelete(distributor)}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('distributors')}</h1>
          <p className="text-muted-foreground">{t('manage_distributors')}</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          {t('add_distributor')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('distributors')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={distributors || []} columns={columns} />
        </CardContent>
      </Card>

      {/* Distributor Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingDistributor ? t('edit_distributor') : t('add_distributor')}
            </DialogTitle>
            <DialogDescription>
              {editingDistributor
                ? t('update_distributor_information')
                : t('create_new_distributor')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">
                    {t('name')} <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="legal_name">{t('legal_name')}</Label>
                  <Input
                    id="legal_name"
                    value={formData.legal_name}
                    onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="email">
                    {t('email')} <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">{t('phone')}</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="registration_number">{t('registration_number')}</Label>
                  <Input
                    id="registration_number"
                    value={formData.registration_number}
                    onChange={(e) =>
                      setFormData({ ...formData, registration_number: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="website">{t('website')}</Label>
                  <Input
                    id="website"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="address_line1">{t('address_line_1')}</Label>
                <Input
                  id="address_line1"
                  value={formData.address_line1}
                  onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address_line2">{t('address_line_2')}</Label>
                <Input
                  id="address_line2"
                  value={formData.address_line2}
                  onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">{t('city')}</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="postal_code">{t('postal_code')}</Label>
                  <Input
                    id="postal_code"
                    value={formData.postal_code}
                    onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">{t('country')}</Label>
                  <Input
                    id="country"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label htmlFor="is_active">{t('active')}</Label>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDialogOpen(false);
                  setEditingDistributor(null);
                  setFormData(emptyForm);
                }}
              >
                {t('cancel')}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editingDistributor ? t('update') : t('create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirm_deletion')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('are_you_sure_delete_distributor', { name: deletingDistributor?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingDistributor && deleteMutation.mutate(deletingDistributor.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
