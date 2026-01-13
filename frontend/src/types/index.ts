// User and Auth types
export const UserRole = {
  ADMIN: "admin",
  RESTRICTED_ADMIN: "restricted_admin",
  DISTRIBUTOR: "distributor",
  PARTNER: "partner",
  FULFILLER: "fulfiller",
} as const;

export type UserRole = typeof UserRole[keyof typeof UserRole];

export interface User {
  id: number | string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_enabled?: boolean;
  last_login?: string;
  user_type?: string;
  distributor_id?: number;
  partner_id?: number;
  created_at: string;
  api_key?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Product types
export interface ProductType {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PriceTier {
  id?: number;
  product_id?: number;
  min_quantity: number;
  max_quantity?: number | null;
  price_per_unit: string;
  period: "month" | "year";
}

export interface Product {
  id: number;
  name: string;
  type_id: string;
  unit: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  price_tiers?: PriceTier[];
  product_type?: ProductType;
}

// Partner/Distributor types
export interface Distributor {
  id: string; // UUID in backend
  name: string;
  legal_name?: string;
  registration_number?: string;
  email?: string;
  phone?: string;
  website?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  postal_code?: string;
  country?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Partner {
  id: string; // UUID in backend
  name: string;
  legal_name?: string;
  registration_number?: string;
  email?: string;
  phone?: string;
  website?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  postal_code?: string;
  country?: string;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// Lead types
export const LeadStatus = {
  NEW: "new",
  CONTACTED: "contacted",
  QUALIFIED: "qualified",
  PROPOSAL: "proposal",
  NEGOTIATION: "negotiation",
  WON: "won",
  LOST: "lost",
} as const;

export type LeadStatus = typeof LeadStatus[keyof typeof LeadStatus];

export interface Lead {
  id: number;
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  customer_company?: string;
  status: LeadStatus;
  source?: string;
  estimated_value?: number;
  expected_close_date?: string;
  notes?: string;
  partner_id?: number;
  distributor_id?: number;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  partner?: Partner;
  distributor?: Distributor;
  created_by?: User;
}

export interface LeadActivity {
  id: number;
  lead_id: number;
  activity_type: string;
  description: string;
  created_by_id: number;
  created_at: string;
  created_by?: User;
}

// Order types
export const OrderStatus = {
  DRAFT: "draft",
  PENDING: "pending",
  PROCESSING: "processing",
  CONFIRMED: "confirmed",
  DELIVERED: "delivered",
  CANCELLED: "cancelled",
} as const;

export type OrderStatus = typeof OrderStatus[keyof typeof OrderStatus];

export interface OrderItem {
  id?: number;
  product_id: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
  duration_months?: number;
  product?: Product;
}

export interface Order {
  id: number;
  order_number: string;
  customer_name: string;
  customer_email: string;
  status: OrderStatus;
  total_amount: number;
  currency: string;
  notes?: string;
  lead_id?: number;
  partner_id?: number;
  distributor_id?: number;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  lead?: Lead;
  partner?: Partner;
  distributor?: Distributor;
  created_by?: User;
}

// Contract types
export const ContractStatus = {
  DRAFT: "draft",
  ACTIVE: "active",
  EXPIRED: "expired",
  TERMINATED: "terminated",
} as const;

export type ContractStatus = typeof ContractStatus[keyof typeof ContractStatus];

export interface Contract {
  id: number;
  contract_number: string;
  customer_id: string;
  customer_name?: string;
  start_date: string;
  end_date?: string;
  status: ContractStatus;
  total_value: number;
  periodicity_months?: number;
  value_per_period?: number;
  currency: string;
  order_id?: number;
  partner_id?: number;
  distributor_id?: number;
  created_at: string;
  updated_at: string;
  order?: Order;
  partner?: Partner;
  distributor?: Distributor;
}

export interface ContractCreateRequest {
  contract_number?: string;
  customer_id: string;
  partner_id?: string;
  distributor_id?: string;
  periodicity_months?: number;
  value_per_period?: number;
  currency?: string;
  activation_date?: string;
  expiration_date?: string;
  notes_internal?: string;
}

// Provider types
export interface ProviderConfig {
  id: number;
  name: string;
  provider_type: string;
  api_key: string;
  api_url?: string;
  is_active: boolean;
  config_json?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ProviderHealth {
  provider_id: number;
  provider_name: string;
  status: "healthy" | "unhealthy";
  response_time_ms?: number;
  last_check: string;
  error_message?: string;
}

// Dashboard types
export interface DashboardMetrics {
  total_leads: number;
  total_orders: number;
  total_revenue: number;
  active_contracts: number;
  recent_leads: Lead[];
  recent_orders: Order[];
  revenue_by_month?: Array<{ month: string; revenue: number }>;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
}

// Pennylane types
export interface PennylaneConnection {
  id: string;
  name: string;
  masked_token: string;
  company_name?: string;
  is_active: boolean;
  last_sync_at?: string;
  last_sync_status?: 'success' | 'partial' | 'failed';
  last_sync_error?: string;
  sync_customers: boolean;
  sync_invoices: boolean;
  sync_quotes: boolean;
  sync_subscriptions: boolean;
  created_at: string;
  updated_at: string;
}

export interface PennylaneConnectionCreate {
  name: string;
  api_token: string;
  sync_customers?: boolean;
  sync_invoices?: boolean;
  sync_quotes?: boolean;
  sync_subscriptions?: boolean;
}

export interface PennylaneConnectionUpdate {
  name?: string;
  api_token?: string;
  is_active?: boolean;
  sync_customers?: boolean;
  sync_invoices?: boolean;
  sync_quotes?: boolean;
  sync_subscriptions?: boolean;
}

export interface PennylaneCustomer {
  id: string;
  connection_id: string;
  pennylane_id: string;
  name: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  postal_code?: string;
  country_code?: string;
  vat_number?: string;
  customer_type?: string;
  delivery_address?: string;
  delivery_city?: string;
  delivery_postal_code?: string;
  delivery_country_code?: string;
  reg_no?: string;
  recipient?: string;
  reference?: string;
  external_reference?: string;
  billing_language?: string;
  payment_conditions?: string;
  notes?: string;
  billing_iban?: string;
  pennylane_created_at?: string;
  pennylane_updated_at?: string;
  synced_at: string;
  connection_name?: string;
}

export interface PennylaneInvoice {
  id: string;
  connection_id: string;
  pennylane_id: string;
  invoice_number?: string;
  status?: string;
  customer_name?: string;
  customer_id?: string;
  amount?: number;
  currency: string;
  issue_date?: string;
  due_date?: string;
  paid_date?: string;
  pdf_url?: string;
  synced_at: string;
  connection_name?: string;
  contract_id?: string;
  contract_number?: string;
  no_contract?: boolean;
}

export interface PennylaneQuote {
  id: string;
  connection_id: string;
  pennylane_id: string;
  quote_number?: string;
  status?: string;
  customer_name?: string;
  customer_id?: string;
  amount?: number;
  currency: string;
  issue_date?: string;
  valid_until?: string;
  accepted_at?: string;
  synced_at: string;
  connection_name?: string;
}

export interface PennylaneSubscription {
  id: string;
  connection_id: string;
  pennylane_id: string;
  customer_name?: string;
  customer_id?: string;
  status?: string;
  amount?: number;
  currency: string;
  interval?: string;
  start_date?: string;
  next_billing_date?: string;
  cancelled_at?: string;
  synced_at: string;
  connection_name?: string;
}

export interface PennylaneConnectionTestResult {
  success: boolean;
  company_name?: string;
  error?: string;
}

export interface PennylaneSyncResult {
  connection_id: string;
  connection_name: string;
  overall_status: 'success' | 'partial' | 'failed';
  results: {
    entity_type: string;
    total_fetched: number;
    created: number;
    updated: number;
    errors: string[];
    success: boolean;
  }[];
  synced_at: string;
}
