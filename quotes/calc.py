"""Plain in-memory quotation objects. Nothing here is stored in the database."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

TWO = Decimal("0.01")


@dataclass
class Item:
    description: str
    hsn_code: str
    quantity: Decimal
    rate: Decimal
    gst_applicable: bool
    gst_percent: int

    @property
    def amount(self):
        return (self.quantity * self.rate).quantize(TWO)

    @property
    def gst_amount(self):
        if not self.gst_applicable:
            return Decimal("0.00")
        return (self.amount * Decimal(self.gst_percent) / Decimal(100)).quantize(TWO)

    @property
    def total(self):
        return self.amount + self.gst_amount


@dataclass
class Quote:
    company_name: str
    company_address: str
    company_gstin: str
    logo_bytes: Optional[bytes]
    estimate_number: str
    date: date
    valid_till: date
    customer_name: str
    customer_address: str
    customer_gstin: str
    notes: str
    terms: str
    items: list = field(default_factory=list)

    @property
    def subtotal(self):
        return sum((i.amount for i in self.items), Decimal("0.00"))

    @property
    def total_gst(self):
        return sum((i.gst_amount for i in self.items), Decimal("0.00"))

    @property
    def grand_total(self):
        return self.subtotal + self.total_gst
