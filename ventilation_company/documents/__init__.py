"""Генератор українських бухгалтерських документів."""

from ventilation_company.documents.invoice import Invoice
from ventilation_company.documents.delivery_note import DeliveryNote
from ventilation_company.documents.act import WorkAct
from ventilation_company.documents.company_info import CompanyInfo, DEFAULT_COMPANY

__all__ = ["Invoice", "DeliveryNote", "WorkAct", "CompanyInfo", "DEFAULT_COMPANY"]
