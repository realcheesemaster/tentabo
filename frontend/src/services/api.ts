import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type {
  User,
  LoginRequest,
  LoginResponse,
  Product,
  Lead,
  LeadActivity,
  Order,
  Contract,
  ContractCreateRequest,
  Distributor,
  Partner,
  ProviderConfig,
  ProviderHealth,
  DashboardMetrics,
  PennylaneConnection,
  PennylaneConnectionCreate,
  PennylaneConnectionUpdate,
  PennylaneCustomer,
  PennylaneInvoice,
  PennylaneQuote,
  PennylaneSubscription,
  PennylaneConnectionTestResult,
  PennylaneSyncResult,
} from "@/types";

// Dynamically determine API URL based on current host
const API_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

// Create axios instance
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Don't redirect on 401 for login endpoint - let the login page handle it
    const isLoginRequest = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLoginRequest) {
      // Token expired or invalid
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>("/api/v1/auth/login", credentials);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>("/api/v1/auth/me");
    return response.data;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
  },
};

// Users API
export const usersApi = {
  getAll: async (skip = 0, limit = 100): Promise<User[]> => {
    const response = await api.get<{ items: User[]; pagination: any } | User[]>("/api/v1/users", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: number): Promise<User> => {
    const response = await api.get<User>(`/api/users/${id}`);
    return response.data;
  },

  create: async (data: Partial<User> & { password: string }): Promise<User> => {
    const response = await api.post<User>("/api/v1/users", data);
    return response.data;
  },

  update: async (id: number, data: Partial<User>): Promise<User> => {
    const response = await api.put<User>(`/api/users/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/users/${id}`);
  },

  generateApiKey: async (userId: number): Promise<{ api_key: string }> => {
    const response = await api.post<{ api_key: string }>(`/api/users/${userId}/api-key`);
    return response.data;
  },

  discoverLdap: async (search?: string, limit: number = 50): Promise<any> => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    params.append('limit', limit.toString());
    const response = await api.get(`/api/v1/users/ldap/discover?${params.toString()}`);
    return response.data;
  },

  enableLdapUser: async (username: string, role: string = 'partner', enabled: boolean = true): Promise<User> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('role', role);
    params.append('enabled', enabled.toString());
    const response = await api.post<User>(`/api/v1/users/ldap/enable?${params.toString()}`);
    return response.data;
  },

  enableUser: async (userId: string, enabled: boolean, reason?: string): Promise<User> => {
    const response = await api.put<User>(`/api/v1/users/${userId}/enable`, {
      enabled,
      reason
    });
    return response.data;
  },

  updateUserRole: async (userId: string, role: string, reason?: string): Promise<User> => {
    const response = await api.put<User>(`/api/v1/users/${userId}/role`, {
      role,
      reason
    });
    return response.data;
  },

  assignCompany: async (userId: string, partnerId?: string | null, distributorId?: string | null): Promise<User> => {
    const params = new URLSearchParams();
    if (partnerId) params.append('partner_id', partnerId);
    if (distributorId) params.append('distributor_id', distributorId);
    const response = await api.put<User>(`/api/v1/users/${userId}/company?${params.toString()}`);
    return response.data;
  },
};

// Products API
export const productsApi = {
  getAll: async (skip = 0, limit = 100): Promise<Product[]> => {
    const response = await api.get<{ items: Product[]; pagination: any } | Product[]>("/api/v1/products", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: number): Promise<Product> => {
    const response = await api.get<Product>(`/api/products/${id}`);
    return response.data;
  },

  create: async (data: Partial<Product>): Promise<Product> => {
    const response = await api.post<Product>("/api/v1/products", data);
    return response.data;
  },

  update: async (id: number, data: Partial<Product>): Promise<Product> => {
    const response = await api.put<Product>(`/api/products/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/products/${id}`);
  },

  calculatePrice: async (productId: number, quantity: number, durationMonths?: number) => {
    const response = await api.post(`/api/products/${productId}/calculate-price`, {
      quantity,
      duration_months: durationMonths,
    });
    return response.data;
  },
};

// Distributors API
export const distributorsApi = {
  getAll: async (skip = 0, limit = 100): Promise<Distributor[]> => {
    const response = await api.get<{ items: Distributor[]; pagination: any } | Distributor[]>("/api/v1/distributors", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: string): Promise<Distributor> => {
    const response = await api.get<Distributor>(`/api/v1/distributors/${id}`);
    return response.data;
  },

  create: async (data: Partial<Distributor>): Promise<Distributor> => {
    const response = await api.post<Distributor>("/api/v1/distributors", data);
    return response.data;
  },

  update: async (id: string, data: Partial<Distributor>): Promise<Distributor> => {
    const response = await api.put<Distributor>(`/api/v1/distributors/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/distributors/${id}`);
  },
};

// Partners API
export const partnersApi = {
  getAll: async (skip = 0, limit = 100): Promise<Partner[]> => {
    const response = await api.get<{ items: Partner[]; pagination: any } | Partner[]>("/api/v1/partners", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: string): Promise<Partner> => {
    const response = await api.get<Partner>(`/api/v1/partners/${id}`);
    return response.data;
  },

  create: async (data: Partial<Partner>): Promise<Partner> => {
    const response = await api.post<Partner>("/api/v1/partners", data);
    return response.data;
  },

  update: async (id: string, data: Partial<Partner>): Promise<Partner> => {
    const response = await api.put<Partner>(`/api/v1/partners/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/partners/${id}`);
  },
};

// Leads API
export const leadsApi = {
  getAll: async (skip = 0, limit = 100): Promise<Lead[]> => {
    const response = await api.get<{ items: Lead[]; pagination: any } | Lead[]>("/api/v1/leads", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: number): Promise<Lead> => {
    const response = await api.get<Lead>(`/api/leads/${id}`);
    return response.data;
  },

  create: async (data: Partial<Lead>): Promise<Lead> => {
    const response = await api.post<Lead>("/api/v1/leads", data);
    return response.data;
  },

  update: async (id: number, data: Partial<Lead>): Promise<Lead> => {
    const response = await api.put<Lead>(`/api/leads/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/leads/${id}`);
  },

  getActivities: async (leadId: number): Promise<LeadActivity[]> => {
    const response = await api.get<LeadActivity[]>(`/api/leads/${leadId}/activities`);
    return response.data;
  },

  addActivity: async (leadId: number, data: Partial<LeadActivity>): Promise<LeadActivity> => {
    const response = await api.post<LeadActivity>(`/api/leads/${leadId}/activities`, data);
    return response.data;
  },

  convertToOrder: async (leadId: number): Promise<Order> => {
    const response = await api.post<Order>(`/api/leads/${leadId}/convert`);
    return response.data;
  },
};

// Orders API
export const ordersApi = {
  getAll: async (skip = 0, limit = 100): Promise<Order[]> => {
    const response = await api.get<{ items: Order[]; pagination: any } | Order[]>("/api/v1/orders", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: number): Promise<Order> => {
    const response = await api.get<Order>(`/api/orders/${id}`);
    return response.data;
  },

  create: async (data: Partial<Order>): Promise<Order> => {
    const response = await api.post<Order>("/api/v1/orders", data);
    return response.data;
  },

  update: async (id: number, data: Partial<Order>): Promise<Order> => {
    const response = await api.put<Order>(`/api/orders/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/orders/${id}`);
  },

  updateStatus: async (id: number, status: string): Promise<Order> => {
    const response = await api.patch<Order>(`/api/orders/${id}/status`, { status });
    return response.data;
  },
};

// Contracts API
export const contractsApi = {
  getAll: async (skip = 0, limit = 100): Promise<Contract[]> => {
    const response = await api.get<{ items: Contract[]; pagination: any } | Contract[]>("/api/v1/contracts", {
      params: { skip, limit },
    });
    return Array.isArray(response.data) ? response.data : (response.data.items !== undefined ? response.data.items : []);
  },

  getById: async (id: number): Promise<Contract> => {
    const response = await api.get<Contract>(`/api/contracts/${id}`);
    return response.data;
  },

  create: async (data: Partial<Contract>): Promise<Contract> => {
    const response = await api.post<Contract>("/api/v1/contracts", data);
    return response.data;
  },

  createContract: async (data: ContractCreateRequest): Promise<Contract> => {
    const response = await api.post<Contract>("/api/v1/contracts/", data);
    return response.data;
  },

  update: async (id: number, data: Partial<Contract>): Promise<Contract> => {
    const response = await api.put<Contract>(`/api/contracts/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/contracts/${id}`);
  },
};

// Providers API
export const providersApi = {
  getAll: async (): Promise<ProviderConfig[]> => {
    const response = await api.get<ProviderConfig[]>("/api/v1/providers");
    return response.data;
  },

  getById: async (id: number): Promise<ProviderConfig> => {
    const response = await api.get<ProviderConfig>(`/api/providers/${id}`);
    return response.data;
  },

  create: async (data: Partial<ProviderConfig>): Promise<ProviderConfig> => {
    const response = await api.post<ProviderConfig>("/api/v1/providers", data);
    return response.data;
  },

  update: async (id: number, data: Partial<ProviderConfig>): Promise<ProviderConfig> => {
    const response = await api.put<ProviderConfig>(`/api/providers/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/providers/${id}`);
  },

  checkHealth: async (id: number): Promise<ProviderHealth> => {
    const response = await api.get<ProviderHealth>(`/api/providers/${id}/health`);
    return response.data;
  },

  switchActive: async (id: number): Promise<ProviderConfig> => {
    const response = await api.post<ProviderConfig>(`/api/providers/${id}/switch`);
    return response.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getMetrics: async (): Promise<DashboardMetrics> => {
    const response = await api.get<DashboardMetrics>("/api/v1/dashboard/metrics");
    return response.data;
  },
};

// Pennylane API
export const pennylaneApi = {
  // Connection management
  getConnections: async (skip = 0, limit = 100): Promise<PennylaneConnection[]> => {
    const response = await api.get<{ items: PennylaneConnection[] }>("/api/v1/pennylane/connections", {
      params: { skip, limit },
    });
    return response.data.items || [];
  },

  getConnection: async (id: string): Promise<PennylaneConnection> => {
    const response = await api.get<PennylaneConnection>(`/api/v1/pennylane/connections/${id}`);
    return response.data;
  },

  createConnection: async (data: PennylaneConnectionCreate): Promise<PennylaneConnection> => {
    const response = await api.post<PennylaneConnection>("/api/v1/pennylane/connections", data);
    return response.data;
  },

  updateConnection: async (id: string, data: PennylaneConnectionUpdate): Promise<PennylaneConnection> => {
    const response = await api.put<PennylaneConnection>(`/api/v1/pennylane/connections/${id}`, data);
    return response.data;
  },

  deleteConnection: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/pennylane/connections/${id}`);
  },

  testConnection: async (id: string): Promise<PennylaneConnectionTestResult> => {
    const response = await api.post<PennylaneConnectionTestResult>(`/api/v1/pennylane/connections/${id}/test`);
    return response.data;
  },

  syncConnection: async (id: string): Promise<PennylaneSyncResult> => {
    const response = await api.post<PennylaneSyncResult>(`/api/v1/pennylane/connections/${id}/sync`);
    return response.data;
  },

  // Customers
  getCustomers: async (
    page = 1,
    pageSize = 25,
    filters?: {
      connection_id?: string;
      search?: string;
      customer_type?: string;
      pennylane_id?: string;
      sort?: string;
    }
  ): Promise<{ items: PennylaneCustomer[]; pagination: any }> => {
    const params: any = { page, page_size: pageSize };
    if (filters?.connection_id) params.connection_id = filters.connection_id;
    if (filters?.search) params.search = filters.search;
    if (filters?.customer_type) params.customer_type = filters.customer_type;
    if (filters?.pennylane_id) params.pennylane_id = filters.pennylane_id;
    if (filters?.sort) params.sort = filters.sort;
    const response = await api.get("/api/v1/pennylane/customers", { params });
    return response.data;
  },

  getCustomer: async (id: string): Promise<PennylaneCustomer & { raw_data: any }> => {
    const response = await api.get(`/api/v1/pennylane/customers/${id}`);
    return response.data;
  },

  // Invoices
  getInvoices: async (
    page = 1,
    pageSize = 25,
    filters?: {
      connection_id?: string;
      status?: string;
      date_from?: string;
      date_to?: string;
      search?: string;
      sort?: string;
      contract_id?: string;
    }
  ): Promise<{ items: PennylaneInvoice[]; pagination: any }> => {
    const params: any = { page, page_size: pageSize };
    if (filters?.connection_id) params.connection_id = filters.connection_id;
    if (filters?.status) params.status = filters.status;
    if (filters?.date_from) params.date_from = filters.date_from;
    if (filters?.date_to) params.date_to = filters.date_to;
    if (filters?.search) params.search = filters.search;
    if (filters?.sort) params.sort = filters.sort;
    if (filters?.contract_id) params.contract_id = filters.contract_id;
    const response = await api.get("/api/v1/pennylane/invoices", { params });
    return response.data;
  },

  getInvoice: async (id: string): Promise<PennylaneInvoice & { raw_data: any }> => {
    const response = await api.get(`/api/v1/pennylane/invoices/${id}`);
    return response.data;
  },

  linkInvoiceToContract: async (
    invoiceId: string,
    contractId: string | null,
    noContract: boolean = false
  ): Promise<{ message: string; contract_id: string | null; no_contract: boolean }> => {
    const response = await api.put(`/api/v1/pennylane/invoices/${invoiceId}/contract`, {
      contract_id: contractId,
      no_contract: noContract,
    });
    return response.data;
  },

  // Quotes
  getQuotes: async (
    page = 1,
    pageSize = 25,
    filters?: {
      connection_id?: string;
      status?: string;
      search?: string;
      sort?: string;
    }
  ): Promise<{ items: PennylaneQuote[]; pagination: any }> => {
    const params: any = { page, page_size: pageSize };
    if (filters?.connection_id) params.connection_id = filters.connection_id;
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;
    if (filters?.sort) params.sort = filters.sort;
    const response = await api.get("/api/v1/pennylane/quotes", { params });
    return response.data;
  },

  getQuote: async (id: string): Promise<PennylaneQuote & { raw_data: any }> => {
    const response = await api.get(`/api/v1/pennylane/quotes/${id}`);
    return response.data;
  },

  // Subscriptions
  getSubscriptions: async (
    page = 1,
    pageSize = 25,
    filters?: {
      connection_id?: string;
      status?: string;
      interval?: string;
      search?: string;
      sort?: string;
    }
  ): Promise<{ items: PennylaneSubscription[]; pagination: any }> => {
    const params: any = { page, page_size: pageSize };
    if (filters?.connection_id) params.connection_id = filters.connection_id;
    if (filters?.status) params.status = filters.status;
    if (filters?.interval) params.interval = filters.interval;
    if (filters?.search) params.search = filters.search;
    if (filters?.sort) params.sort = filters.sort;
    const response = await api.get("/api/v1/pennylane/subscriptions", { params });
    return response.data;
  },

  getSubscription: async (id: string): Promise<PennylaneSubscription & { raw_data: any }> => {
    const response = await api.get(`/api/v1/pennylane/subscriptions/${id}`);
    return response.data;
  },
};
