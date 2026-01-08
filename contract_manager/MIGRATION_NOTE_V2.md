# Database Migration Note V2

## Important: Major Schema Changes

The database schema has been significantly updated with new tables and fields.

### Steps to Update:

1. **Backup your data** (if needed):
   ```bash
   cd backend
   cp contracts.db contracts.db.backup
   ```

2. **Delete the old database**:
   ```bash
   rm contracts.db
   cd ..
   ```

3. **Restart the application**:
   ```bash
   ./run.sh
   ```

   The new database will be created automatically with the updated schema.

### What's New:

#### 1. **Product Table**
- Products are now stored in a separate table
- Products can be managed via the Products page
- Product dropdown in contract form
- Products cannot be deleted if used in contracts

#### 2. **Customer Categories**
- Customers can be categorized as:
  - End User
  - Reseller
  - Distributor
- Category is displayed in contracts table

#### 3. **Duration in Months**
- Contract duration is now stored in **months** (not years)
- ARR calculation: `value / (duration_in_months / 12)`
- PDF parser automatically converts years to months

#### 4. **Navigation**
- Added navigation bar to switch between:
  - Contracts page (main)
  - Products management page

### Schema Changes:

**New Tables:**
- **products** (id, name, description)

**Updated Tables:**
- **customers** - Added `category` field (end-user/reseller/distributor)
- **contracts** - Changed:
  - `product` (String) → `product_id` (ForeignKey to products)
  - `contract_duration` (Float in years) → (Integer in months)

### API Changes:

**New Endpoints:**
- `GET /products` - Products management page
- `GET /api/products` - List all products
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product (if not in use)

**Updated Endpoints:**
- `POST /api/contracts` - Now requires `product_name` and `customer_category`
