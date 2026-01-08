# Tentabo PRM Frontend

A modern, bilingual (French/English) React frontend for the Tentabo Partner Relationship Management system.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **shadcn/ui** for UI components
- **Tailwind CSS** for styling
- **React Router** for navigation
- **TanStack Query** (React Query) for server state management
- **react-i18next** for internationalization
- **react-hook-form** for form handling
- **axios** for API calls
- **Lucide React** for icons

## Features

- JWT-based authentication
- Role-based access control (Admin, Distributor, Partner)
- Bilingual support (French/English)
- Responsive design
- Dark mode ready
- Real-time data synchronization
- Complete CRUD operations for:
  - Products
  - Users
  - Partners
  - Distributors
  - Leads (with Kanban view)
  - Orders
  - Contracts
  - Provider settings

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Update API URL in .env if needed
# VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

The application will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Project Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui components
│   ├── common/          # Reusable components (DataTable, StatusBadge, etc.)
│   ├── layout/          # Layout components (Sidebar, Header)
│   ├── leads/           # Lead-specific components
│   ├── orders/          # Order-specific components
│   └── products/        # Product-specific components
├── contexts/
│   └── AuthContext.tsx  # Authentication context
├── hooks/               # Custom React hooks
├── lib/
│   ├── i18n.ts         # i18n configuration
│   └── utils.ts        # Utility functions
├── locales/
│   ├── fr/             # French translations
│   └── en/             # English translations
├── pages/              # Page components
├── services/
│   └── api.ts          # API client and services
├── types/
│   └── index.ts        # TypeScript types
├── App.tsx             # Main app component with routing
└── main.tsx            # Application entry point
```

## Default Credentials

Use the credentials from the backend setup:

- **Admin**: admin / admin123
- **Distributor**: dist1 / dist123
- **Partner**: partner1 / partner123

## Key Features

### Authentication

- JWT token-based authentication
- Automatic token refresh
- Redirect to login on unauthorized access
- Secure token storage

### Role-Based Access

- **Admin**: Full access to all features
- **Distributor**: Access to partners, leads, orders, contracts
- **Partner**: Access to leads, orders, contracts

### Lead Management

- Kanban board view for visual pipeline management
- List view with filtering
- Status tracking (New → Contacted → Qualified → Proposal → Negotiation → Won/Lost)
- Activity timeline
- Convert to order functionality

### Order Management

- Create orders from leads or standalone
- Product selection with pricing calculation
- Status workflow
- Order history

### Multi-language Support

- French (default)
- English
- Language switcher in header
- All UI text translated

## API Integration

The frontend communicates with the backend API through:

- Axios instance with automatic JWT token attachment
- Error interceptor for handling 401 errors
- Type-safe API calls
- React Query for caching and synchronization

## Development

### Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/layout/Sidebar.tsx`
4. Add translations in `src/locales/`

### Adding a New Component

1. Create component in appropriate directory
2. Export from index file if needed
3. Add TypeScript types
4. Add translations if needed

### Styling

This project uses Tailwind CSS with shadcn/ui components. To add custom styles:

1. Use Tailwind utility classes
2. Add custom CSS in `src/index.css`
3. Follow shadcn/ui conventions for component variants

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## Troubleshooting

### API Connection Issues

- Ensure backend is running at the configured API URL
- Check browser console for CORS errors
- Verify authentication token is valid

### Build Errors

- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

### Translation Issues

- Check that all translation keys exist in both fr/ and en/ directories
- Verify i18n initialization in main.tsx

## License

Proprietary - Tentabo PRM
