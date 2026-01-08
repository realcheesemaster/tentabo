import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { partnersApi } from '@/services/api';
import { type Partner } from '@/types';
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

interface PartnerFormData {
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

const emptyForm: PartnerFormData = {
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

export const Partners: React.FC = () => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPartner, setEditingPartner] = useState<Partner | null>(null);
  const [deletingPartner, setDeletingPartner] = useState<Partner | null>(null);
  const [formData, setFormData] = useState<PartnerFormData>(emptyForm);

  const { data: partners, isLoading } = useQuery({
    queryKey: ['partners'],
    queryFn: () => partnersApi.getAll(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: Partial<Partner>) => partnersApi.create(data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('partner_created_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      setDialogOpen(false);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_create_partner'),
        variant: 'destructive',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Partner> }) =>
      partnersApi.update(id, data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('partner_updated_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      setDialogOpen(false);
      setEditingPartner(null);
      setFormData(emptyForm);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_update_partner'),
        variant: 'destructive',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => partnersApi.delete(id),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('partner_deleted_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['partners'] });
      setDeleteDialogOpen(false);
      setDeletingPartner(null);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_delete_partner'),
        variant: 'destructive',
      });
    },
  });

  const handleAdd = () => {
    setEditingPartner(null);
    setFormData(emptyForm);
    setDialogOpen(true);
  };

  const handleEdit = (partner: Partner) => {
    setEditingPartner(partner);
    setFormData({
      name: partner.name || '',
      legal_name: partner.legal_name || '',
      registration_number: partner.registration_number || '',
      email: partner.email || '',
      phone: partner.phone || '',
      website: partner.website || '',
      address_line1: partner.address_line1 || '',
      address_line2: partner.address_line2 || '',
      city: partner.city || '',
      postal_code: partner.postal_code || '',
      country: partner.country || 'France',
      is_active: partner.is_active,
      notes: partner.notes || '',
    });
    setDialogOpen(true);
  };

  const handleDelete = (partner: Partner) => {
    setDeletingPartner(partner);
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

    if (editingPartner) {
      updateMutation.mutate({ id: editingPartner.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const columns: Column<Partner>[] = [
    {
      key: 'name',
      header: t('name'),
    },
    {
      key: 'email',
      header: t('email'),
      render: (partner) => partner.email || '-',
    },
    {
      key: 'phone',
      header: t('phone'),
      render: (partner) => partner.phone || '-',
    },
    {
      key: 'city',
      header: t('city'),
      render: (partner) => partner.city || '-',
    },
    {
      key: 'country',
      header: t('country'),
      render: (partner) => partner.country || '-',
    },
    {
      key: 'is_active',
      header: t('status'),
      render: (partner) => (
        <Badge variant={partner.is_active ? 'success' : 'secondary'}>
          {partner.is_active ? t('active') : t('inactive')}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: t('created_at'),
      render: (partner) => formatDate(partner.created_at),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (partner) => (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleEdit(partner)}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleDelete(partner)}
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
          <h1 className="text-3xl font-bold">{t('partners')}</h1>
          <p className="text-muted-foreground">{t('manage_business_partners')}</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          {t('add_partner')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('partners')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={partners || []} columns={columns} />
        </CardContent>
      </Card>

      {/* Partner Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingPartner ? t('edit_partner') : t('add_partner')}
            </DialogTitle>
            <DialogDescription>
              {editingPartner
                ? t('update_partner_information')
                : t('create_new_partner')}
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
                  setEditingPartner(null);
                  setFormData(emptyForm);
                }}
              >
                {t('cancel')}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editingPartner ? t('update') : t('create')}
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
              {t('are_you_sure_delete_partner', { name: deletingPartner?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingPartner && deleteMutation.mutate(deletingPartner.id)}
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
