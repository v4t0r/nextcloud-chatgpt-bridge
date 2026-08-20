from __future__ import annotations

from decimal import Decimal

from nextcloud_chatgpt_bridge.household.invoices import InvoiceReviewer
from nextcloud_chatgpt_bridge.household.models import (
    InvoiceCheckOutcome,
    InvoiceReviewStatus,
)

TEXT_INVOICE = """Supplier: Example Energy GmbH
Invoice number: INV-2026-0042
Invoice date: 2026-08-01
Due date: 2026-08-15
Net amount: 100,00 EUR
VAT: 19,00 EUR
Grand total: 119,00 EUR
Payment reference: ENERGY-0042
IBAN: DE89 3704 0044 0532 0130 00
"""


def test_text_invoice_review_extracts_fields_without_approving_payment():
    review = InvoiceReviewer().review(
        TEXT_INVOICE.encode(),
        path="Household/Invoices/Inbox/energy.txt",
        content_type="text/plain",
        expected_currency="EUR",
    )

    assert review.status == InvoiceReviewStatus.READY_FOR_HUMAN_REVIEW
    assert review.invoice_number == "INV-2026-0042"
    assert review.supplier == "Example Energy GmbH"
    assert review.net_amount == Decimal("100.00")
    assert review.tax_amount == Decimal("19.00")
    assert review.gross_amount == Decimal("119.00")
    assert review.iban_last4 == "3000"
    assert "DE89" not in str(review.model_dump())
    assert "did not approve" in review.decision_boundary
    assert any(
        check.code == "amount_consistency"
        and check.outcome == InvoiceCheckOutcome.PASSED
        for check in review.checks
    )


def test_image_invoice_requires_explicit_ocr_adapter():
    review = InvoiceReviewer().review(
        b"fake-image-bytes",
        path="Household/Invoices/Inbox/scan.png",
        content_type="image/png",
        expected_currency="EUR",
    )

    assert review.status == InvoiceReviewStatus.MANUAL_REVIEW_REQUIRED
    assert review.extraction_method == "ocr_required"
    assert review.extracted_character_count == 0
    assert any(check.outcome == InvoiceCheckOutcome.MANUAL for check in review.checks)


def test_ubl_xml_invoice_extracts_structured_amounts():
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <ID>XML-2026-1</ID>
  <IssueDate>2026-08-02</IssueDate>
  <DueDate>2026-08-20</DueDate>
  <DocumentCurrencyCode>EUR</DocumentCurrencyCode>
  <AccountingSupplierParty><Party><PartyLegalEntity><RegistrationName>XML Supplier</RegistrationName></PartyLegalEntity></Party></AccountingSupplierParty>
  <TaxTotal><TaxAmount currencyID="EUR">19.00</TaxAmount></TaxTotal>
  <LegalMonetaryTotal>
    <TaxExclusiveAmount currencyID="EUR">100.00</TaxExclusiveAmount>
    <PayableAmount currencyID="EUR">119.00</PayableAmount>
  </LegalMonetaryTotal>
</Invoice>"""

    review = InvoiceReviewer().review(
        payload,
        path="Household/Invoices/Inbox/invoice.xml",
        content_type="application/xml",
        expected_currency="EUR",
    )

    assert review.invoice_number == "XML-2026-1"
    assert review.supplier == "XML Supplier"
    assert review.gross_amount == Decimal("119.00")
    assert review.status == InvoiceReviewStatus.READY_FOR_HUMAN_REVIEW
