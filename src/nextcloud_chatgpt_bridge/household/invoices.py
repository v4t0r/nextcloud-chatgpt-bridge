from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from typing import Protocol

from defusedxml import ElementTree as ET
from pypdf import PdfReader

from nextcloud_chatgpt_bridge.household.models import (
    InvoiceCheck,
    InvoiceCheckOutcome,
    InvoiceReview,
    InvoiceReviewStatus,
)

_MAX_EXTRACTED_CHARACTERS = 200_000
_MAX_PDF_PAGES = 100
_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}[./-]\d{2}[./-]\d{4})\b")
_AMOUNT_PATTERN = re.compile(
    r"(?:(EUR|USD|CHF|GBP|€|\$|£)\s*)?(-?[0-9][0-9 .'\u00a0]*(?:[,.][0-9]{2}))\s*(EUR|USD|CHF|GBP|€|\$|£)?",
    re.IGNORECASE,
)
_IBAN_PATTERN = re.compile(r"\b([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})\b")


class InvoiceExtractionError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ExtractedDocument:
    source_type: str
    method: str
    text: str
    page_count: int | None = None
    truncated: bool = False
    warning: str | None = None


class InvoiceTextExtractor(Protocol):
    def extract(
        self,
        payload: bytes,
        *,
        file_name: str,
        content_type: str | None,
    ) -> ExtractedDocument: ...


class DefaultInvoiceTextExtractor:
    """Local deterministic extraction. Images are marked for OCR instead of guessed."""

    def extract(
        self,
        payload: bytes,
        *,
        file_name: str,
        content_type: str | None,
    ) -> ExtractedDocument:
        suffix = PurePosixPath(file_name).suffix.lower()
        if suffix == ".pdf" or content_type == "application/pdf":
            return self._extract_pdf(payload)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"} or (
            content_type and content_type.startswith("image/")
        ):
            return ExtractedDocument(
                source_type="image",
                method="ocr_required",
                text="",
                warning="Image invoices require an explicitly configured OCR or vision adapter",
            )
        if suffix == ".xml" or content_type in {"application/xml", "text/xml"}:
            text = self._decode_text(payload)
            return self._bounded("xml", "xml", text)
        if suffix in {".txt", ".md", ".csv", ".json"} or (
            content_type and content_type.startswith("text/")
        ):
            return self._bounded("text", "utf8", self._decode_text(payload))
        return ExtractedDocument(
            source_type="unknown",
            method="unsupported",
            text="",
            warning="Invoice file type is not supported by the local extractor",
        )

    @staticmethod
    def _decode_text(payload: bytes) -> str:
        try:
            return payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvoiceExtractionError("Invoice text is not valid UTF-8") from exc

    def _extract_pdf(self, payload: bytes) -> ExtractedDocument:
        try:
            reader = PdfReader(BytesIO(payload), strict=False)
            if reader.is_encrypted:
                return ExtractedDocument(
                    source_type="pdf",
                    method="encrypted_pdf",
                    text="",
                    page_count=len(reader.pages),
                    warning="Encrypted PDF requires manual review",
                )
            if len(reader.pages) > _MAX_PDF_PAGES:
                raise InvoiceExtractionError("Invoice PDF exceeds the page safety limit")
            parts: list[str] = []
            remaining = _MAX_EXTRACTED_CHARACTERS
            extraction_truncated = False
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if len(page_text) > remaining:
                    parts.append(page_text[:remaining])
                    extraction_truncated = True
                    break
                parts.append(page_text)
                remaining -= len(page_text) + 1
                if remaining <= 0:
                    extraction_truncated = True
                    break
            text = "\n".join(parts)
        except InvoiceExtractionError:
            raise
        except Exception as exc:
            raise InvoiceExtractionError("Invoice PDF could not be parsed safely") from exc
        result = self._bounded(
            "pdf",
            "pypdf",
            text,
            page_count=len(reader.pages),
            extraction_truncated=extraction_truncated,
        )
        if not result.text.strip():
            return ExtractedDocument(
                source_type="pdf",
                method="ocr_required",
                text="",
                page_count=len(reader.pages),
                warning="PDF contains no extractable text and requires OCR or vision review",
            )
        return result

    @staticmethod
    def _bounded(
        source_type: str,
        method: str,
        text: str,
        *,
        page_count: int | None = None,
        extraction_truncated: bool = False,
    ) -> ExtractedDocument:
        normalized = text.replace("\x00", "")
        truncated = extraction_truncated or len(normalized) > _MAX_EXTRACTED_CHARACTERS
        return ExtractedDocument(
            source_type=source_type,
            method=method,
            text=normalized[:_MAX_EXTRACTED_CHARACTERS],
            page_count=page_count,
            truncated=truncated,
            warning="Extracted invoice text was truncated at the safety limit" if truncated else None,
        )


class InvoiceReviewer:
    def __init__(self, extractor: InvoiceTextExtractor | None = None) -> None:
        self.extractor = extractor or DefaultInvoiceTextExtractor()

    def review(
        self,
        payload: bytes,
        *,
        path: str,
        content_type: str | None,
        expected_currency: str,
    ) -> InvoiceReview:
        file_name = PurePosixPath(path).name
        digest = sha256(payload).hexdigest()
        try:
            extracted = self.extractor.extract(
                payload,
                file_name=file_name,
                content_type=content_type,
            )
        except InvoiceExtractionError as exc:
            extracted = ExtractedDocument(
                source_type=PurePosixPath(file_name).suffix.lower().lstrip(".") or "unknown",
                method="manual_review",
                text="",
                warning=str(exc),
            )

        fields = self._extract_fields(extracted.text, payload, extracted.source_type)
        currency = fields.get("currency")
        checks: list[InvoiceCheck] = []
        if extracted.warning:
            checks.append(
                InvoiceCheck(
                    code="extraction_warning",
                    outcome=InvoiceCheckOutcome.MANUAL,
                    message=extracted.warning,
                )
            )
        self._required_check(checks, "invoice_number", fields.get("invoice_number"))
        self._required_check(checks, "invoice_date", fields.get("invoice_date"))
        self._required_check(checks, "gross_amount", fields.get("gross_amount"))

        if currency is None:
            checks.append(
                InvoiceCheck(
                    code="currency_missing",
                    outcome=InvoiceCheckOutcome.WARNING,
                    message="Invoice currency could not be determined",
                )
            )
        elif currency != expected_currency:
            checks.append(
                InvoiceCheck(
                    code="currency_mismatch",
                    outcome=InvoiceCheckOutcome.WARNING,
                    message=f"Invoice currency {currency} differs from household currency {expected_currency}",
                )
            )
        else:
            checks.append(
                InvoiceCheck(
                    code="currency_match",
                    outcome=InvoiceCheckOutcome.PASSED,
                    message="Invoice currency matches the household profile",
                )
            )

        invoice_date = fields.get("invoice_date")
        due_date = fields.get("due_date")
        if isinstance(invoice_date, date) and isinstance(due_date, date):
            if due_date < invoice_date:
                checks.append(
                    InvoiceCheck(
                        code="due_date_order",
                        outcome=InvoiceCheckOutcome.WARNING,
                        message="Due date is earlier than invoice date",
                    )
                )
            else:
                checks.append(
                    InvoiceCheck(
                        code="due_date_order",
                        outcome=InvoiceCheckOutcome.PASSED,
                        message="Due date is not earlier than invoice date",
                    )
                )

        net = fields.get("net_amount")
        tax = fields.get("tax_amount")
        gross = fields.get("gross_amount")
        if isinstance(net, Decimal) and isinstance(tax, Decimal) and isinstance(gross, Decimal):
            delta = abs((net + tax) - gross)
            checks.append(
                InvoiceCheck(
                    code="amount_consistency",
                    outcome=(
                        InvoiceCheckOutcome.PASSED
                        if delta <= Decimal("0.02")
                        else InvoiceCheckOutcome.WARNING
                    ),
                    message=(
                        "Net amount plus tax matches gross amount"
                        if delta <= Decimal("0.02")
                        else "Net amount plus tax does not match gross amount"
                    ),
                )
            )

        manual = not extracted.text.strip() or any(
            check.outcome == InvoiceCheckOutcome.MANUAL for check in checks
        )
        required_missing = any(
            check.code.startswith("missing_") for check in checks
        )
        return InvoiceReview(
            path=path,
            file_name=file_name,
            file_sha256=digest,
            file_size=len(payload),
            source_type=extracted.source_type,
            extraction_method=extracted.method,
            page_count=extracted.page_count,
            extracted_character_count=len(extracted.text),
            text_truncated=extracted.truncated,
            invoice_number=_as_optional_str(fields.get("invoice_number")),
            supplier=_as_optional_str(fields.get("supplier")),
            invoice_date=invoice_date if isinstance(invoice_date, date) else None,
            due_date=due_date if isinstance(due_date, date) else None,
            currency=currency if isinstance(currency, str) else None,
            net_amount=net if isinstance(net, Decimal) else None,
            tax_amount=tax if isinstance(tax, Decimal) else None,
            gross_amount=gross if isinstance(gross, Decimal) else None,
            payment_reference=_as_optional_str(fields.get("payment_reference")),
            iban_last4=_as_optional_str(fields.get("iban_last4")),
            status=(
                InvoiceReviewStatus.MANUAL_REVIEW_REQUIRED
                if manual or required_missing
                else InvoiceReviewStatus.READY_FOR_HUMAN_REVIEW
            ),
            checks=checks,
        )

    @staticmethod
    def _required_check(checks: list[InvoiceCheck], field: str, value: object) -> None:
        checks.append(
            InvoiceCheck(
                code=f"{field}_present" if value is not None else f"missing_{field}",
                outcome=(
                    InvoiceCheckOutcome.PASSED
                    if value is not None
                    else InvoiceCheckOutcome.MANUAL
                ),
                message=(
                    f"Invoice {field.replace('_', ' ')} was extracted"
                    if value is not None
                    else f"Invoice {field.replace('_', ' ')} requires manual verification"
                ),
            )
        )

    def _extract_fields(self, text: str, payload: bytes, source_type: str) -> dict[str, object]:
        fields: dict[str, object] = {}
        if source_type == "xml" and text:
            fields.update(_extract_xml_fields(payload))

        lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
        invoice_number = _labeled_text(
            lines,
            ("rechnungsnummer", "rechnungsnr", "invoice number", "invoice no"),
            limit=64,
        )
        supplier = _labeled_text(
            lines,
            ("lieferant", "rechnungssteller", "supplier", "vendor"),
            limit=128,
        )
        payment_reference = _labeled_text(
            lines,
            ("verwendungszweck", "zahlungsreferenz", "payment reference", "reference"),
            limit=128,
        )
        fields.setdefault("invoice_number", invoice_number)
        fields.setdefault("supplier", supplier)
        fields.setdefault("payment_reference", payment_reference)
        fields.setdefault(
            "invoice_date",
            _labeled_date(lines, ("rechnungsdatum", "invoice date", "issued")),
        )
        fields.setdefault(
            "due_date",
            _labeled_date(lines, ("fälligkeitsdatum", "fällig am", "due date", "payable by")),
        )

        gross, currency = _labeled_amount(
            lines,
            ("gesamtbetrag", "rechnungsbetrag", "zahlbetrag", "amount due", "grand total", "total"),
        )
        net, net_currency = _labeled_amount(
            lines,
            ("nettobetrag", "net amount", "subtotal"),
        )
        tax, tax_currency = _labeled_amount(
            lines,
            ("umsatzsteuer", "mehrwertsteuer", "mwst", "vat", "tax amount"),
        )
        fields.setdefault("gross_amount", gross)
        fields.setdefault("net_amount", net)
        fields.setdefault("tax_amount", tax)
        fields.setdefault("currency", currency or net_currency or tax_currency)

        iban_match = _IBAN_PATTERN.search(text.upper())
        if iban_match:
            normalized_iban = re.sub(r"\s+", "", iban_match.group(1))
            fields.setdefault("iban_last4", normalized_iban[-4:])
        return {key: value for key, value in fields.items() if value is not None}


def _labeled_text(lines: list[str], labels: tuple[str, ...], *, limit: int) -> str | None:
    for line in lines:
        folded = line.casefold()
        for label in labels:
            index = folded.find(label)
            if index < 0:
                continue
            value = line[index + len(label) :].lstrip(" \t:#-–—")
            if value:
                return value[:limit]
    return None


def _labeled_date(lines: list[str], labels: tuple[str, ...]) -> date | None:
    value = _labeled_text(lines, labels, limit=64)
    if value is None:
        return None
    match = _DATE_PATTERN.search(value)
    return _parse_date(match.group(1)) if match else None


def _parse_date(value: str) -> date | None:
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _labeled_amount(
    lines: list[str],
    labels: tuple[str, ...],
) -> tuple[Decimal | None, str | None]:
    value = _labeled_text(lines, labels, limit=128)
    if value is None:
        return None, None
    match = _AMOUNT_PATTERN.search(value)
    if not match:
        return None, None
    try:
        amount = _parse_decimal(match.group(2))
    except InvalidOperation:
        return None, None
    return amount, _normalize_currency(match.group(1) or match.group(3))


def _parse_decimal(value: str) -> Decimal:
    normalized = value.replace(" ", "").replace("\u00a0", "").replace("'", "")
    comma = normalized.rfind(",")
    dot = normalized.rfind(".")
    if comma >= 0 and dot >= 0:
        decimal_separator = "," if comma > dot else "."
        thousands_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif comma >= 0:
        normalized = normalized.replace(".", "").replace(",", ".")
    return Decimal(normalized).quantize(Decimal("0.01"))


def _normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.upper()
    return {"€": "EUR", "$": "USD", "£": "GBP"}.get(normalized, normalized)


def _extract_xml_fields(payload: bytes) -> dict[str, object]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return {}

    def local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def first_text(names: tuple[str, ...]) -> str | None:
        wanted = set(names)
        for element in root.iter():
            if local_name(element.tag) in wanted and element.text and element.text.strip():
                return " ".join(element.text.split())
        return None

    fields: dict[str, object] = {}
    direct_id = next(
        (
            child.text.strip()
            for child in list(root)
            if local_name(child.tag) == "ID" and child.text and child.text.strip()
        ),
        None,
    )
    fields["invoice_number"] = direct_id or first_text(("ID",))
    fields["supplier"] = first_text(("RegistrationName", "Name"))
    fields["invoice_date"] = _parse_date(first_text(("IssueDate", "DateTimeString")) or "")
    fields["due_date"] = _parse_date(first_text(("DueDate",)) or "")
    fields["currency"] = _normalize_currency(
        first_text(("DocumentCurrencyCode", "InvoiceCurrencyCode"))
    )
    for key, names in (
        ("gross_amount", ("PayableAmount", "DuePayableAmount", "GrandTotalAmount")),
        ("net_amount", ("TaxExclusiveAmount", "LineTotalAmount")),
        ("tax_amount", ("TaxAmount", "TaxTotalAmount")),
    ):
        value = first_text(names)
        if value:
            try:
                fields[key] = _parse_decimal(value)
            except InvalidOperation:
                pass
    fields["payment_reference"] = first_text(("PaymentID", "PaymentReference"))
    iban = first_text(("IBANID",))
    if iban:
        fields["iban_last4"] = re.sub(r"\s+", "", iban)[-4:]
    return {key: value for key, value in fields.items() if value is not None}


def _as_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
