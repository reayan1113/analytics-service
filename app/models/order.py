"""
Read-only models for existing order tables
DO NOT modify these tables - they are managed by the Order Service
"""
from sqlalchemy import Column, BigInteger, DateTime, Enum, String, Integer, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database import OrderBase
import enum


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"


class Order(OrderBase):
    """Read-only Order model - DO NOT MODIFY"""
    __tablename__ = "orders"
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(6), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    table_id = Column(BigInteger, nullable=False)
    total_amount = Column(Numeric(10, 2))
    user_id = Column(BigInteger, nullable=False)
    
    # Relationship to order items
    items = relationship("OrderItem", back_populates="order")


class OrderItem(OrderBase):
    """Read-only OrderItem model - DO NOT MODIFY"""
    __tablename__ = "order_items"
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id = Column(BigInteger, nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    order_id = Column(BigInteger, ForeignKey('orders.id'), nullable=False)
    
    # Relationship to order
    order = relationship("Order", back_populates="items")
