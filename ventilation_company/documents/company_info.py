"""Реквізити фірми та клієнта для документів."""

from dataclasses import dataclass


@dataclass
class CompanyInfo:
    """Реквізити компанії (фірми або клієнта)."""
    name: str = ""                    # Повна назва
    edrpou: str = ""                # ЄДРПОУ / РНОКПП
    address: str = ""               # Юридична адреса
    phone: str = ""                 # Телефон
    email: str = ""                 # Email
    bank_name: str = ""             # Назва банку
    bank_account: str = ""          # Р/р (IBAN)
    bank_mfo: str = ""              # МФО
    director: str = ""              # ПІБ директора
    accountant: str = ""            # ПІБ бухгалтера
    tax_system: str = "загальна"    # загальна / єдиний податок
    vat_payer: bool = True          # Платник ПДВ

    def validate(self) -> list[str]:
        """Перевірити заповненість обов'язкових полів."""
        errors = []
        if not self.name:
            errors.append("Назва компанії")
        if not self.edrpou:
            errors.append("ЄДРПОУ")
        if not self.address:
            errors.append("Адреса")
        if not self.bank_account:
            errors.append("Р/р")
        return errors


# ── За замовчуванням: реквізити ТОВ "Твердук Вент" ───────────
DEFAULT_COMPANY = CompanyInfo(
    name='ТОВ "Твердук Вент"',
    edrpou="12345678",
    address="м. Тернопіль, вул. Промислова, 15",
    phone="+38 (0352) 12-34-56",
    email="info@tverduk-vent.com.ua",
    bank_name='АТ КБ "ПриватБанк"',
    bank_account="UA123456789000000000000000000",
    bank_mfo="305299",
    director="Твердук Іван Петрович",
    accountant="Твердук Марія Іванівна",
    tax_system="загальна",
    vat_payer=True,
)
