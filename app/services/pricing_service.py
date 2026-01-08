"""
Pricing Service

Handles all pricing calculations including:
- Tier-based progressive pricing
- Duration discounts
- Price breakdowns
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.core import Product, PriceTier, Duration

logger = logging.getLogger(__name__)


class PricingService:
    """
    Service for calculating product prices with progressive tiers and duration discounts

    Uses Decimal for all calculations to ensure financial precision.
    Never uses float for money calculations.
    """

    @staticmethod
    def _quantize(value: Decimal, places: int = 2) -> Decimal:
        """
        Quantize a Decimal to a specific number of decimal places

        Args:
            value: Decimal value to quantize
            places: Number of decimal places (default 2 for currency)

        Returns:
            Quantized Decimal
        """
        quantizer = Decimal('0.01') if places == 2 else Decimal('0.0001')
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_progressive_price(
        product_id: UUID,
        quantity: int,
        duration_id: Optional[UUID],
        db: Session
    ) -> Dict[str, Any]:
        """
        Calculate price for a product with progressive pricing and duration discount

        Args:
            product_id: Product UUID
            quantity: Quantity to purchase
            duration_id: Optional duration for discount
            db: Database session

        Returns:
            Dict with price breakdown including:
            - product_id, product_name, quantity
            - unit_price: Price per unit based on tier
            - subtotal: quantity * unit_price
            - duration_months: If duration specified
            - discount_percentage: Duration discount
            - discount_amount: Calculated discount
            - total: Final price after discount
            - currency: Always EUR
            - breakdown: Detailed tier information

        Raises:
            HTTPException: If product or duration not found, or if no price tier matches
        """
        # Get product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found"
            )

        # Check if product is active
        is_active = product.is_active if isinstance(product.is_active, bool) else product.is_active == 'true'
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} is not active"
            )

        # Find matching price tier
        matching_tier = None
        for tier in product.price_tiers:
            if tier.min_quantity <= quantity:
                if tier.max_quantity is None or quantity <= tier.max_quantity:
                    matching_tier = tier
                    break

        if not matching_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No price tier found for quantity {quantity}"
            )

        # Calculate base price
        unit_price = Decimal(str(matching_tier.price_per_unit))
        subtotal = PricingService._quantize(unit_price * quantity)

        # Get duration discount if specified
        duration_months = None
        discount_percentage = Decimal('0')
        duration_discount = Decimal('0')

        if duration_id:
            duration = db.query(Duration).filter(Duration.id == duration_id).first()
            if not duration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Duration {duration_id} not found"
                )

            duration_months = duration.months
            discount_percentage = Decimal(str(duration.discount_percentage))

            # Calculate discount amount
            if discount_percentage > 0:
                duration_discount = PricingService._quantize(
                    subtotal * (discount_percentage / Decimal('100'))
                )

        # Calculate final total
        total = PricingService._quantize(subtotal - duration_discount)

        # Build detailed breakdown
        breakdown = {
            "tier": {
                "min_quantity": matching_tier.min_quantity,
                "max_quantity": matching_tier.max_quantity,
                "price_per_unit": float(unit_price),
                "period": matching_tier.period,
            },
            "calculation": {
                "quantity": quantity,
                "unit_price": float(unit_price),
                "subtotal": float(subtotal),
            }
        }

        if duration_id and duration_months:
            breakdown["duration"] = {
                "months": duration_months,
                "discount_percentage": float(discount_percentage),
                "discount_amount": float(duration_discount),
            }

        result = {
            "product_id": str(product_id),
            "product_name": product.name,
            "product_type": product.type,
            "product_unit": product.unit,
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "duration_months": duration_months,
            "discount_percentage": discount_percentage,
            "discount_amount": duration_discount,
            "total": total,
            "currency": "EUR",
            "breakdown": breakdown,
        }

        logger.info(
            f"Calculated price for {product.name}: "
            f"qty={quantity}, unit_price={unit_price}, total={total}"
        )

        return result

    @staticmethod
    def calculate_order_totals(
        items: list,
        db: Session
    ) -> Dict[str, Decimal]:
        """
        Calculate totals for an entire order

        Args:
            items: List of items with product_id, quantity, duration_id
            db: Database session

        Returns:
            Dict with subtotal, discount_amount, tax_amount (0 for now), total_amount

        Raises:
            HTTPException: If any item is invalid
        """
        subtotal = Decimal('0')
        discount_amount = Decimal('0')

        for item in items:
            price_calc = PricingService.calculate_progressive_price(
                product_id=item['product_id'],
                quantity=item['quantity'],
                duration_id=item.get('duration_id'),
                db=db
            )

            subtotal += price_calc['subtotal']
            discount_amount += price_calc['discount_amount']

        # Tax calculation would go here (not implemented yet)
        tax_amount = Decimal('0')

        total_amount = PricingService._quantize(subtotal - discount_amount + tax_amount)

        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
        }
