"""
FastAPI dependencies for common operations

Provides:
- Pagination parameters
- Sorting parameters
- Filter parameters
- Multi-tenant query filters
"""

import logging
from typing import Optional, Union
from enum import Enum
from fastapi import Query, Depends
from sqlalchemy.orm import Session, Query as SQLQuery

from app.database import get_db
from app.models.auth import User, AdminUser, UserRole

logger = logging.getLogger(__name__)


class SortOrder(str, Enum):
    """Sort order enum"""
    ASC = "asc"
    DESC = "desc"


class PaginationParams:
    """
    Pagination parameters for list endpoints

    Usage:
        @app.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (starting from 1)"),
        page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


class SortParams:
    """
    Sorting parameters for list endpoints

    Usage:
        @app.get("/items")
        async def list_items(sort: SortParams = Depends()):
            query = query.order_by(sort.get_order_by(Item.created_at))
    """
    def __init__(
        self,
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order

    def get_order_by(self, default_column):
        """
        Get SQLAlchemy order by clause

        Args:
            default_column: Default column to sort by if sort_by not specified

        Returns:
            SQLAlchemy order by clause
        """
        if self.sort_order == SortOrder.ASC:
            return default_column.asc()
        else:
            return default_column.desc()


class MultiTenantFilter:
    """
    Multi-tenant filtering based on user role

    Implements the following access rules:
    - Admin/AdminUser: See all data
    - Distributor: See only their partners' data
    - Partner: See only their own data
    - Fulfiller: See all data
    """

    @staticmethod
    def filter_partners_query(
        query: SQLQuery,
        current_user: Union[User, AdminUser],
        partner_model
    ) -> SQLQuery:
        """
        Filter partners query based on user role

        Args:
            query: SQLAlchemy query to filter
            current_user: Current authenticated user
            partner_model: Partner model class

        Returns:
            Filtered query
        """
        # Admin and AdminUser see everything
        if isinstance(current_user, AdminUser):
            return query

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return query

            # Distributors see only their partners
            if current_user.role == UserRole.DISTRIBUTOR:
                if current_user.distributor_id:
                    # Import here to avoid circular imports
                    from app.models.partner import DistributorPartner

                    # Join with distributor_partners to filter
                    query = query.join(
                        DistributorPartner,
                        partner_model.id == DistributorPartner.partner_id
                    ).filter(
                        DistributorPartner.distributor_id == current_user.distributor_id,
                        DistributorPartner.is_active == True
                    )
                else:
                    # Distributor user without distributor_id sees nothing
                    query = query.filter(False)

                return query

            # Partners see only their own data
            if current_user.role == UserRole.PARTNER:
                if current_user.partner_id:
                    query = query.filter(partner_model.id == current_user.partner_id)
                else:
                    # Partner user without partner_id sees nothing
                    query = query.filter(False)

                return query

        # Default: no access
        return query.filter(False)

    @staticmethod
    def filter_distributors_query(
        query: SQLQuery,
        current_user: Union[User, AdminUser],
        distributor_model
    ) -> SQLQuery:
        """
        Filter distributors query based on user role

        Args:
            query: SQLAlchemy query to filter
            current_user: Current authenticated user
            distributor_model: Distributor model class

        Returns:
            Filtered query
        """
        # Admin and AdminUser see everything
        if isinstance(current_user, AdminUser):
            return query

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return query

            # Distributors see only their own record
            if current_user.role == UserRole.DISTRIBUTOR:
                if current_user.distributor_id:
                    query = query.filter(distributor_model.id == current_user.distributor_id)
                else:
                    query = query.filter(False)

                return query

            # Partners see their associated distributors
            if current_user.role == UserRole.PARTNER:
                if current_user.partner_id:
                    from app.models.partner import DistributorPartner

                    query = query.join(
                        DistributorPartner,
                        distributor_model.id == DistributorPartner.distributor_id
                    ).filter(
                        DistributorPartner.partner_id == current_user.partner_id,
                        DistributorPartner.is_active == True
                    )
                else:
                    query = query.filter(False)

                return query

        # Default: no access
        return query.filter(False)

    @staticmethod
    def filter_orders_query(
        query: SQLQuery,
        current_user: Union[User, AdminUser],
        order_model
    ) -> SQLQuery:
        """
        Filter orders query based on user role

        Args:
            query: SQLAlchemy query to filter
            current_user: Current authenticated user
            order_model: Order model class

        Returns:
            Filtered query
        """
        # Admin and AdminUser see everything
        if isinstance(current_user, AdminUser):
            return query

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return query

            # Distributors see only their orders
            if current_user.role == UserRole.DISTRIBUTOR:
                if current_user.distributor_id:
                    query = query.filter(order_model.distributor_id == current_user.distributor_id)
                else:
                    query = query.filter(False)

                return query

            # Partners see only their orders
            if current_user.role == UserRole.PARTNER:
                if current_user.partner_id:
                    query = query.filter(order_model.partner_id == current_user.partner_id)
                else:
                    query = query.filter(False)

                return query

        # Default: no access
        return query.filter(False)

    @staticmethod
    def filter_contracts_query(
        query: SQLQuery,
        current_user: Union[User, AdminUser],
        contract_model
    ) -> SQLQuery:
        """
        Filter contracts query based on user role

        Args:
            query: SQLAlchemy query to filter
            current_user: Current authenticated user
            contract_model: Contract model class

        Returns:
            Filtered query
        """
        # Admin and AdminUser see everything
        if isinstance(current_user, AdminUser):
            return query

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return query

            # Distributors see only their contracts
            if current_user.role == UserRole.DISTRIBUTOR:
                if current_user.distributor_id:
                    query = query.filter(contract_model.distributor_id == current_user.distributor_id)
                else:
                    query = query.filter(False)

                return query

            # Partners see only their contracts
            if current_user.role == UserRole.PARTNER:
                if current_user.partner_id:
                    query = query.filter(contract_model.partner_id == current_user.partner_id)
                else:
                    query = query.filter(False)

                return query

        # Default: no access
        return query.filter(False)

    @staticmethod
    def filter_leads_query(
        query: SQLQuery,
        current_user: Union[User, AdminUser],
        lead_model
    ) -> SQLQuery:
        """
        Filter leads query based on user role

        Args:
            query: SQLAlchemy query to filter
            current_user: Current authenticated user
            lead_model: Lead model class

        Returns:
            Filtered query
        """
        # Admin and AdminUser see everything
        if isinstance(current_user, AdminUser):
            return query

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return query

            # Distributors see only their leads
            if current_user.role == UserRole.DISTRIBUTOR:
                if current_user.distributor_id:
                    query = query.filter(lead_model.distributor_id == current_user.distributor_id)
                else:
                    query = query.filter(False)

                return query

            # Partners see only their leads
            if current_user.role == UserRole.PARTNER:
                if current_user.partner_id:
                    query = query.filter(lead_model.partner_id == current_user.partner_id)
                else:
                    query = query.filter(False)

                return query

        # Default: no access
        return query.filter(False)

    @staticmethod
    def can_access_partner(
        current_user: Union[User, AdminUser],
        partner_id: str,
        db: Session
    ) -> bool:
        """
        Check if user can access a specific partner

        Args:
            current_user: Current authenticated user
            partner_id: Partner ID to check
            db: Database session

        Returns:
            True if user can access, False otherwise
        """
        # Admin and AdminUser can access everything
        if isinstance(current_user, AdminUser):
            return True

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return True

            # Partner can access their own data
            if current_user.role == UserRole.PARTNER:
                return str(current_user.partner_id) == str(partner_id)

            # Distributor can access their partners
            if current_user.role == UserRole.DISTRIBUTOR and current_user.distributor_id:
                from app.models.partner import DistributorPartner

                association = db.query(DistributorPartner).filter(
                    DistributorPartner.distributor_id == current_user.distributor_id,
                    DistributorPartner.partner_id == partner_id,
                    DistributorPartner.is_active == True
                ).first()

                return association is not None

        return False

    @staticmethod
    def can_access_distributor(
        current_user: Union[User, AdminUser],
        distributor_id: str,
        db: Session
    ) -> bool:
        """
        Check if user can access a specific distributor

        Args:
            current_user: Current authenticated user
            distributor_id: Distributor ID to check
            db: Database session

        Returns:
            True if user can access, False otherwise
        """
        # Admin and AdminUser can access everything
        if isinstance(current_user, AdminUser):
            return True

        if isinstance(current_user, User):
            if current_user.role in [UserRole.ADMIN, UserRole.FULFILLER]:
                return True

            # Distributor can access their own data
            if current_user.role == UserRole.DISTRIBUTOR:
                return str(current_user.distributor_id) == str(distributor_id)

            # Partner can access their associated distributors
            if current_user.role == UserRole.PARTNER and current_user.partner_id:
                from app.models.partner import DistributorPartner

                association = db.query(DistributorPartner).filter(
                    DistributorPartner.partner_id == current_user.partner_id,
                    DistributorPartner.distributor_id == distributor_id,
                    DistributorPartner.is_active == True
                ).first()

                return association is not None

        return False


def get_multi_tenant_filter() -> MultiTenantFilter:
    """Dependency to get multi-tenant filter instance"""
    return MultiTenantFilter()
