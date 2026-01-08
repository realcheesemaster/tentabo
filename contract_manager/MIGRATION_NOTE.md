# Database Migration Note

## Important: Database Schema Changed

The database schema has been significantly updated to include a separate Customer table. If you have existing data, you'll need to recreate the database.

### Steps to Update:

1. **Backup your data** (if needed):
   - The old database is at `backend/contracts.db`
   - You can keep a copy before deleting

2. **Delete the old database**:
   ```bash
   cd backend
   rm contracts.db
   ```

3. **Restart the application**:
   ```bash
   cd ..
   ./run.sh
   ```

   The new database will be created automatically with the updated schema.

### What's New:

- **Separate Customer Table**: Customers are now stored separately from contracts
- **Customer Matching**: When uploading PDFs, the system tries to match customers using fuzzy name matching
- **Autocomplete**: Type a company name to see suggestions from existing customers
- **Auto-fill**: Selecting a customer automatically fills address and national ID
- **Auto-update**: If customer data changes, the database is updated
- **Sortable DataTable**: Contracts are displayed in a sortable, searchable table

### Schema Changes:

**Before:**
- Contract table with embedded customer fields

**After:**
- Customer table (id, company_name, company_address, national_identifier)
- Contract table with foreign key to Customer (customer_id)
