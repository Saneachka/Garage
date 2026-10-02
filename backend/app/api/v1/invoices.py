from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from app.db.session import get_db
from app.models.invoice import Invoice, Payment, InvoiceStatus, PaymentMethod, PaymentStatus
from app.models.order import Order
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceWithRelations, InvoiceListResponse,
    PaymentCreate, PaymentResponse
)
from app.api.deps import get_current_active_user, require_manager


router = APIRouter(prefix="/invoices", tags=["Invoices"])


def generate_invoice_number() -> str:
    import random
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


@router.post("", response_model=InvoiceWithRelations, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    # Verify order
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == invoice_data.order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.COMPLETED, OrderStatus.INVOICED]:
        raise HTTPException(status_code=400, detail="Order must be completed before invoicing")

    # Check if invoice already exists for this order
    result = await db.execute(select(Invoice).where(Invoice.order_id == order.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invoice already exists for this order")

    # Calculate totals from order
    subtotal = sum(float(item.total_price) for item in order.items)
    tax = invoice_data.tax
    discount = invoice_data.discount
    total = subtotal + tax - discount

    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        order_id=order.id,
        customer_id=order.customer_id,
        status=InvoiceStatus.DRAFT,
        subtotal=subtotal,
        tax=tax,
        discount=discount,
        total=total,
        due_date=invoice_data.due_date,
        notes=invoice_data.notes,
    )
    db.add(invoice)

    # Update order status
    order.status = OrderStatus.INVOICED

    await db.commit()

    # Reload with relations
    query = select(Invoice).options(
        selectinload(Invoice.customer),
        selectinload(Invoice.order).selectinload(Order.items),
        selectinload(Invoice.payments),
    ).where(Invoice.id == invoice.id)
    result = await db.execute(query)
    return result.scalar_one()


@router.get("", response_model=list[InvoiceListResponse])
async def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(
        Invoice.id,
        Invoice.invoice_number,
        Invoice.customer_id,
        User.full_name.label("customer_name"),
        Invoice.order_id,
        Order.order_number,
        Invoice.status,
        Invoice.total,
        Invoice.paid_amount,
        (Invoice.total - Invoice.paid_amount).label("balance_due"),
        Invoice.due_date,
        Invoice.issued_at,
    ).join(User, Invoice.customer_id == User.id).join(Order, Invoice.order_id == Order.id)

    if current_user.role.value == "customer":
        query = query.where(Invoice.customer_id == current_user.id)

    if status:
        query = query.where(Invoice.status == status)
    if customer_id and current_user.role.value in ["admin", "manager"]:
        query = query.where(Invoice.customer_id == customer_id)
    if start_date:
        query = query.where(Invoice.issued_at >= start_date)
    if end_date:
        query = query.where(Invoice.issued_at <= end_date)
    if overdue_only:
        query = query.where(
            Invoice.due_date < datetime.utcnow(),
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])
        )

    query = query.order_by(Invoice.issued_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.mappings().all()


@router.get("/{invoice_id}", response_model=InvoiceWithRelations)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Invoice).options(
        selectinload(Invoice.customer),
        selectinload(Invoice.order).selectinload(Order.items).selectinload(Order.items.service_type),
        selectinload(Invoice.order).selectinload(Order.items).selectinload(Order.items.part),
        selectinload(Invoice.payments),
    ).where(Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role.value == "customer" and invoice.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = invoice_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    # Recalculate total if tax/discount changed
    if "tax" in update_data or "discount" in update_data:
        invoice.total = invoice.subtotal + invoice.tax - invoice.discount

    # Update status based on payment
    if invoice.paid_amount >= invoice.total:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
    elif invoice.paid_amount > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft invoices can be sent")

    invoice.status = InvoiceStatus.SENT
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def add_payment(
    invoice_id: int,
    payment_data: PaymentCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status in [InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED]:
        raise HTTPException(status_code=400, detail="Cannot add payment to cancelled/refunded invoice")

    payment = Payment(
        invoice_id=invoice.id,
        amount=payment_data.amount,
        method=PaymentMethod(payment_data.method),
        status=PaymentStatus.COMPLETED,
        notes=payment_data.notes,
        processed_at=datetime.utcnow(),
    )
    db.add(payment)

    # Update invoice
    invoice.paid_amount += payment_data.amount
    if invoice.paid_amount >= invoice.total:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
    elif invoice.paid_amount > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/{invoice_id}/payments", response_model=list[PaymentResponse])
async def list_payments(
    invoice_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role.value == "customer" and invoice.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status not in [InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Can only delete draft or cancelled invoices")

    # Reset order status
    order_result = await db.execute(select(Order).where(Order.id == invoice.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = OrderStatus.COMPLETED

    await db.delete(invoice)
    await db.commit()