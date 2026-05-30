import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models.account import Account
from models.order import Order
from models.user import User
from schemas.order import OrderCreate, OrderResponse
from services.account_hub import hub
from services.market_feed import feed
from services.matching_engine import fill_order

router = APIRouter(prefix="/orders", tags=["orders"])


async def _account_for(db, user) -> Account:
    return await db.scalar(
        select(Account).where(Account.user_id == user.id).with_for_update()
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    account = await _account_for(db, user)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    order = Order(
        account_id=account.id,
        symbol=body.symbol,
        side=body.side,
        order_type=body.order_type,
        quantity=body.quantity,
        price=body.price,
        trigger_price=body.trigger_price,
        status="open",
    )
    db.add(order)
    await db.flush()

    price = None
    if body.order_type == "market":
        price = feed.get_price(body.symbol)
        if price is None:
            await db.rollback()
            raise HTTPException(status_code=503, detail="No market price available")
        try:
            await fill_order(db, account, order, price, feed.get_price)
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))

    await db.commit()
    await db.refresh(order)

    if body.order_type == "market" and price is not None:
        await hub.push(
            account.id,
            {"type": "fill", "symbol": order.symbol, "side": order.side,
             "quantity": str(order.quantity), "price": str(price)},
        )

    return order


@router.get("", response_model=list[OrderResponse])
async def list_open_orders(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Order]:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return list(
        (
            await db.scalars(
                select(Order)
                .where(Order.account_id == account.id, Order.status == "open")
                .order_by(Order.created_at.desc())
            )
        ).all()
    )


@router.delete("/{order_id}")
async def cancel_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    account = await db.scalar(select(Account).where(Account.user_id == user.id))
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    order = await db.scalar(
        select(Order).where(Order.id == order_id, Order.account_id == account.id).with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "open":
        raise HTTPException(status_code=400, detail="Only open orders can be cancelled")
    order.status = "cancelled"
    await db.commit()
    return {"status": "cancelled"}
