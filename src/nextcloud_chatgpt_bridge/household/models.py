from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class InvoiceReviewStatus(StrEnum):
    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class InvoiceCheckOutcome(StrEnum):
    PASSED = "pass"
    WARNING = "warning"
    MANUAL = "manual"


class HouseholdProfileRecord(BaseModel):
    profile_id: str = Field(min_length=16, max_length=256)
    tenant_id: str = Field(min_length=16, max_length=256)
    connection_id: str = Field(min_length=16, max_length=256)
    display_name: str = Field(min_length=1, max_length=128)
    invoice_inbox_path: str = Field(min_length=1, max_length=4096)
    invoice_archive_path: str = Field(min_length=1, max_length=4096)
    review_report_path: str = Field(min_length=1, max_length=4096)
    default_currency: str = Field(min_length=3, max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HouseholdProfileSummary(BaseModel):
    profile_id: str
    connection_id: str
    display_name: str
    invoice_inbox_path: str
    invoice_archive_path: str
    review_report_path: str
    default_currency: str
    created_at: datetime
    updated_at: datetime


class HouseholdWorkspaceResult(BaseModel):
    profile_id: str
    folders: list[str]
    ready: bool = True


class InvoiceCandidate(BaseModel):
    path: str
    name: str
    size: int
    content_type: str | None = None
    last_modified: str | None = None
    requires_ocr: bool = False


class InvoiceCheck(BaseModel):
    code: str
    outcome: InvoiceCheckOutcome
    message: str


class InvoiceReview(BaseModel):
    path: str
    file_name: str
    file_sha256: str
    file_size: int
    source_type: str
    extraction_method: str
    page_count: int | None = None
    extracted_character_count: int = 0
    text_truncated: bool = False
    invoice_number: str | None = None
    supplier: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    gross_amount: Decimal | None = None
    payment_reference: str | None = None
    iban_last4: str | None = None
    previously_reviewed: bool = False
    status: InvoiceReviewStatus
    checks: list[InvoiceCheck]
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decision_boundary: str = (
        "Human approval is required; the bridge did not approve, book, pay, or transmit payment."
    )


class SavedInvoiceReview(BaseModel):
    profile_id: str
    report_path: str
    saved: bool
    review: InvoiceReview
