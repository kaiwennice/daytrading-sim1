import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OrderType = Literal["market", "limit", "stop_loss", "take_profit"]
Side = Literal["buy", "sell"]


class OrderCreate(BaseModel):
    symbol: str
    side: Side
    order_type: OrderType
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    trigger_price: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_fields(self):
        if self.order_type == "limit" and self.price is None:
            raise ValueError("limit order requires price")
        if self.order_type in ("stop_loss", "take_profit") and self.trigger_price is None:
            raise ValueError("trigger order requires trigger_price")
        if self.order_type in ("stop_loss", "take_profit") and self.side != "sell":
            raise ValueError("stop_loss/take_profit must be sell-to-close")
        return self


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    trigger_price: Decimal | None
    status: str
    created_at: datetime
