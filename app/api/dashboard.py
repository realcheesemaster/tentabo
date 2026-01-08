from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.auth import AdminUser, User
from app.models import Lead, Order, Contract, Product

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"]
)

@router.get("/metrics")
async def get_dashboard_metrics(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get dashboard metrics for the current user"""

    # Get totals
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    active_contracts = db.query(func.count(Contract.id)).filter(
        Contract.status == "active"
    ).scalar() or 0

    # Calculate total revenue from orders
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.status.in_(["sent", "in_fulfillment", "fulfilled"])
    ).scalar() or 0.0

    # Get recent leads (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_leads = db.query(Lead).filter(
        Lead.created_at >= seven_days_ago
    ).order_by(Lead.created_at.desc()).limit(10).all()

    # Get recent orders (last 7 days)
    recent_orders = db.query(Order).filter(
        Order.created_at >= seven_days_ago
    ).order_by(Order.created_at.desc()).limit(10).all()

    # Format the response
    return {
        "total_leads": total_leads,
        "total_orders": total_orders,
        "active_contracts": active_contracts,
        "total_revenue": float(total_revenue),
        "recent_leads": [
            {
                "id": lead.id,
                "customer_name": lead.customer_name,
                "customer_email": lead.customer_email,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            }
            for lead in recent_leads
        ],
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "total_amount": float(order.total_amount) if order.total_amount else 0,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
            for order in recent_orders
        ]
    }