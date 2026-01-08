import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { usersApi, partnersApi, distributorsApi } from '@/services/api';
import { type User } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';
import { DataTable, type Column } from '@/components/common/DataTable';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { UserPlus, Search, RefreshCw, Check, X } from 'lucide-react';

// Component for LDAP user enable action
const LdapUserEnableAction: React.FC<{
  user: LdapUser;
  onEnable: (username: string, role: string, enabled: boolean) => void
}> = ({ user, onEnable }) => {
  const { t } = useTranslation('common');
  const [role, setRole] = useState('partner');
  const [enabled, setEnabled] = useState(true);

  return (
    <div className="flex items-center gap-2">
      <Select value={role} onValueChange={setRole}>
        <SelectTrigger className="w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="partner">{t('role_partner')}</SelectItem>
          <SelectItem value="distributor">{t('role_distributor')}</SelectItem>
          <SelectItem value="admin">{t('role_admin')}</SelectItem>
        </SelectContent>
      </Select>
      <Switch checked={enabled} onCheckedChange={setEnabled} />
      <Button
        size="sm"
        variant="default"
        onClick={() => onEnable(user.username, role, enabled)}
      >
        <UserPlus className="h-4 w-4 mr-1" />
        {t('enable')}
      </Button>
    </div>
  );
};

interface LdapUser {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  display_name: string | null;
  department: string | null;
  exists_in_db: boolean;
  is_enabled: boolean;
  role: string | null;
  user_id: string | null;
}

export const Users: React.FC = () => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [ldapSearch, setLdapSearch] = useState('');
  const [selectedTab, setSelectedTab] = useState('enabled');

  // Query for enabled users
  const { data: users, isLoading: usersLoading, error: usersError } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.getAll(),
  });

  // Query for partners
  const { data: partners } = useQuery({
    queryKey: ['partners'],
    queryFn: () => partnersApi.getAll(),
  });

  // Query for distributors
  const { data: distributors } = useQuery({
    queryKey: ['distributors'],
    queryFn: () => distributorsApi.getAll(),
  });

  // Query for LDAP users
  const { data: ldapData, isLoading: ldapLoading, refetch: refetchLdap } = useQuery({
    queryKey: ['ldap-users', ldapSearch],
    queryFn: async () => {
      const data = await usersApi.discoverLdap(ldapSearch);
      // Add id field to each LDAP user for DataTable compatibility
      if (data?.ldap_users) {
        data.ldap_users = data.ldap_users.map((user: any) => ({
          ...user,
          id: user.user_id || user.username, // Use user_id if exists, otherwise username
        }));
      }
      return data;
    },
    enabled: selectedTab === 'ldap',
  });

  // Enable LDAP user mutation
  const enableUserMutation = useMutation({
    mutationFn: ({ username, role, enabled }: { username: string; role: string; enabled: boolean }) =>
      usersApi.enableLdapUser(username, role, enabled),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('user_enabled_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['ldap-users'] });
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_enable_user'),
        variant: 'destructive',
      });
    },
  });

  // Enable/Disable user mutation
  const toggleUserMutation = useMutation({
    mutationFn: ({ userId, enabled }: { userId: string; enabled: boolean }) =>
      usersApi.enableUser(userId, enabled),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('user_status_updated'),
      });
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['ldap-users'] });
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_update_user'),
        variant: 'destructive',
      });
    },
  });

  // Update role mutation
  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      usersApi.updateUserRole(userId, role),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('user_role_updated'),
      });
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['ldap-users'] });
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_update_role'),
        variant: 'destructive',
      });
    },
  });

  // Assign company mutation
  const assignCompanyMutation = useMutation({
    mutationFn: ({ userId, partnerId, distributorId }: { userId: string; partnerId?: string | null; distributorId?: string | null }) =>
      usersApi.assignCompany(userId, partnerId, distributorId),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('user_company_assigned'),
      });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_assign_company'),
        variant: 'destructive',
      });
    },
  });

  const authorizedColumns: Column<User>[] = [
    {
      key: 'username',
      header: t('username'),
    },
    {
      key: 'email',
      header: t('email'),
    },
    {
      key: 'full_name',
      header: t('name'),
    },
    {
      key: 'role',
      header: t('role_label'),
      render: (user) => (
        <Select
          value={user.role}
          onValueChange={(value) => updateRoleMutation.mutate({ userId: String(user.id), role: value })}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="admin">{t('role_admin')}</SelectItem>
            <SelectItem value="partner">{t('role_partner')}</SelectItem>
            <SelectItem value="distributor">{t('role_distributor')}</SelectItem>
          </SelectContent>
        </Select>
      ),
    },
    {
      key: 'company',
      header: t('company'),
      render: (user) => {
        // For ADMIN users: show "System Admin" (no company)
        if (user.role === 'admin' || user.role === 'restricted_admin') {
          return <span className="text-muted-foreground">{t('system_admin')}</span>;
        }

        // For PARTNER role users: dropdown of all partners
        if (user.role === 'partner') {
          const currentPartnerId = user.partner_id ? String(user.partner_id) : 'none';
          return (
            <Select
              value={currentPartnerId}
              onValueChange={(value) => {
                const partnerId = value === 'none' ? null : value;
                assignCompanyMutation.mutate({
                  userId: String(user.id),
                  partnerId,
                  distributorId: null
                });
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder={t('select_partner')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t('none')}</SelectItem>
                {partners?.map((partner) => (
                  <SelectItem key={partner.id} value={partner.id}>
                    {partner.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }

        // For DISTRIBUTOR role users: dropdown of all distributors
        if (user.role === 'distributor') {
          const currentDistributorId = user.distributor_id ? String(user.distributor_id) : 'none';
          return (
            <Select
              value={currentDistributorId}
              onValueChange={(value) => {
                const distributorId = value === 'none' ? null : value;
                assignCompanyMutation.mutate({
                  userId: String(user.id),
                  partnerId: null,
                  distributorId
                });
              }}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder={t('select_distributor')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t('none')}</SelectItem>
                {distributors?.map((distributor) => (
                  <SelectItem key={distributor.id} value={distributor.id}>
                    {distributor.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }

        return <span className="text-muted-foreground">-</span>;
      },
    },
    {
      key: 'is_enabled',
      header: t('status'),
      render: (user) => (
        <div className="flex items-center gap-2">
          <Switch
            checked={user.is_enabled}
            onCheckedChange={(checked) =>
              toggleUserMutation.mutate({ userId: String(user.id), enabled: checked })
            }
          />
          <Badge variant={user.is_enabled ? 'success' : 'secondary'}>
            {user.is_enabled ? t('enabled') : t('disabled')}
          </Badge>
        </div>
      ),
    },
    {
      key: 'last_login',
      header: t('last_login'),
      render: (user) => user.last_login ? formatDate(user.last_login) : t('never'),
    },
    {
      key: 'created_at',
      header: t('created_at'),
      render: (user) => formatDate(user.created_at),
    },
  ];

  const ldapColumns: Column<LdapUser>[] = [
    {
      key: 'username',
      header: t('username'),
    },
    {
      key: 'email',
      header: t('email'),
      render: (user) => {
        const email = user.email;
        if (!email) return '-';
        // Handle array of emails (some LDAP users have multiple)
        if (email.startsWith('[')) {
          const emails = JSON.parse(email.replace(/'/g, '"'));
          return emails[0];
        }
        return email;
      },
    },
    {
      key: 'full_name',
      header: t('name'),
      render: (user) => user.full_name || '-',
    },
    {
      key: 'department',
      header: t('department'),
      render: (user) => user.department || '-',
    },
    {
      key: 'status',
      header: t('status'),
      render: (user) => {
        if (user.exists_in_db) {
          return (
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              <Badge variant={user.is_enabled ? 'success' : 'secondary'}>
                {user.is_enabled ? t('enabled') : t('disabled')}
              </Badge>
            </div>
          );
        }
        return (
          <div className="flex items-center gap-2">
            <X className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-muted-foreground">{t('not_enabled')}</span>
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (user) => {
        if (user.exists_in_db) {
          if (user.user_id) {
            return (
              <Button
                size="sm"
                variant={user.is_enabled ? 'outline' : 'default'}
                onClick={() =>
                  toggleUserMutation.mutate({ userId: user.user_id!, enabled: !user.is_enabled })
                }
              >
                {user.is_enabled ? t('disable') : t('enable')}
              </Button>
            );
          }
          return null;
        }

        return (
          <LdapUserEnableAction
            user={user}
            onEnable={(username, role, enabled) =>
              enableUserMutation.mutate({ username, role, enabled })
            }
          />
        );
      },
    },
  ];

  if (usersLoading && selectedTab === 'enabled') {
    return <LoadingSpinner />;
  }

  // Show error if user doesn't have permission
  if (usersError && selectedTab === 'enabled') {
    const errorMessage = (usersError as any)?.response?.data?.detail || (usersError as any)?.message || 'Failed to load users';
    const is403 = (usersError as any)?.response?.status === 403;

    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">{t('users')}</h1>
          <p className="text-muted-foreground">{t('manage_system_users')}</p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <p className="text-destructive font-semibold mb-2">
                {is403 ? t('access_denied') : t('error')}
              </p>
              <p className="text-muted-foreground">
                {is403 ? t('admin_privileges_required') : errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{t('users')}</h1>
        <p className="text-muted-foreground">{t('manage_system_users')}</p>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList>
          <TabsTrigger value="enabled">
            {t('enabled_users')} {users && `(${users.length})`}
          </TabsTrigger>
          <TabsTrigger value="ldap">
            {t('ldap_directory')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="enabled">
          <Card>
            <CardHeader>
              <CardTitle>{t('enabled_users')}</CardTitle>
            </CardHeader>
            <CardContent>
              {users && users.length > 0 ? (
                <DataTable data={users} columns={authorizedColumns} />
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>{t('no_enabled_users')}</p>
                  <p className="mt-2">{t('enable_users_from_ldap')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ldap">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{t('ldap_directory')}</span>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                    <Input
                      placeholder={t('search_users')}
                      value={ldapSearch}
                      onChange={(e) => setLdapSearch(e.target.value)}
                      className="pl-8 w-64"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          refetchLdap();
                        }
                      }}
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchLdap()}
                    disabled={ldapLoading}
                  >
                    <RefreshCw className={`h-4 w-4 ${ldapLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ldapLoading ? (
                <LoadingSpinner />
              ) : ldapData?.ldap_users ? (
                <>
                  <p className="text-sm text-muted-foreground mb-4">
                    {ldapData.message}
                  </p>
                  <DataTable data={ldapData.ldap_users} columns={ldapColumns} />
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>{t('unable_to_connect_ldap')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};