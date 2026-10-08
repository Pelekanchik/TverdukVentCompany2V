"""Тести автонумерації договорів (ДГ-YYYYMMDD-NNN)."""

from datetime import date

from ventilation_company.services import contract_numbering


class TestComputeNextNumber:
    def test_first_number_of_the_day(self):
        assert contract_numbering.compute_next_number([], date(2026, 10, 8)) == "ДГ-20261008-001"

    def test_increments_after_existing(self):
        existing = ["ДГ-20261008-001", "ДГ-20261008-002"]
        assert (
            contract_numbering.compute_next_number(existing, date(2026, 10, 8)) == "ДГ-20261008-003"
        )

    def test_other_days_ignored(self):
        existing = ["ДГ-20261007-009", "ДГ-20260901-123"]
        assert (
            contract_numbering.compute_next_number(existing, date(2026, 10, 8)) == "ДГ-20261008-001"
        )

    def test_garbage_ignored(self):
        existing = ["", None, "ДГ-XXXX-999", "ДГ-20261008", "ДГ-20261008-abc"]
        assert (
            contract_numbering.compute_next_number(existing, date(2026, 10, 8)) == "ДГ-20261008-001"
        )

    def test_gap_in_sequence_takes_max(self):
        existing = ["ДГ-20261008-001", "ДГ-20261008-005"]
        assert (
            contract_numbering.compute_next_number(existing, date(2026, 10, 8)) == "ДГ-20261008-006"
        )


class TestEnsureContractNumber:
    def test_existing_number_returned_unchanged(self, monkeypatch):
        def _fail_update(*_a, **_k):  # pragma: no cover — не має викликатись
            raise AssertionError("update не має викликатись для існуючого номера")

        monkeypatch.setattr(contract_numbering.ProjectRepository, "update", _fail_update)
        data = {"contract_number": "ДГ-20260101-042"}
        assert contract_numbering.ensure_contract_number(7, data) == "ДГ-20260101-042"
        assert data["contract_number"] == "ДГ-20260101-042"

    def test_new_number_generated_and_saved(self, monkeypatch):
        import re

        updates = []
        monkeypatch.setattr(contract_numbering, "_taken_numbers", lambda key: ["ДГ-20990101-001"])
        monkeypatch.setattr(
            contract_numbering.ProjectRepository,
            "update",
            staticmethod(lambda pid, data: updates.append((pid, data)) or {"id": pid}),
        )
        data: dict = {}
        number = contract_numbering.ensure_contract_number(7, data)
        # Інший день у «виданих» → послідовність починається з -001 сьогодні
        assert re.fullmatch(r"ДГ-\d{8}-001", number)
        assert updates == [(7, {"contract_number": number})]
        assert data["contract_number"] == number

    def test_update_failure_does_not_block(self, monkeypatch):
        monkeypatch.setattr(contract_numbering, "_taken_numbers", lambda key: [])

        def _boom(*_a, **_k):
            raise RuntimeError("БД недоступна")

        monkeypatch.setattr(contract_numbering.ProjectRepository, "update", staticmethod(_boom))
        data: dict = {}
        number = contract_numbering.ensure_contract_number(3, data)
        assert number.startswith("ДГ-")
        assert "contract_number" not in data  # не закріпився — але договір не заблоковано


class TestEnsureDocumentNumber:
    """Узагальнена нумерація: рахунок (Р) і акт (АК)."""

    def test_invoice_prefix_and_key(self, monkeypatch):
        import re

        updates = []
        monkeypatch.setattr(contract_numbering, "_taken_numbers", lambda key: [])
        monkeypatch.setattr(
            contract_numbering.ProjectRepository,
            "update",
            staticmethod(lambda pid, data: updates.append((pid, data)) or {"id": pid}),
        )
        data: dict = {}
        number = contract_numbering.ensure_document_number(5, data, "invoice_number")
        assert re.fullmatch(r"Р-\d{8}-001", number)
        assert updates == [(5, {"invoice_number": number})]
        assert data["invoice_number"] == number

    def test_act_prefix(self, monkeypatch):
        import re

        monkeypatch.setattr(contract_numbering, "_taken_numbers", lambda key: [])
        monkeypatch.setattr(
            contract_numbering.ProjectRepository,
            "update",
            staticmethod(lambda pid, data: {"id": pid}),
        )
        number = contract_numbering.ensure_document_number(5, {}, "act_number")
        assert re.fullmatch(r"АК-\d{8}-001", number)

    def test_existing_returned_and_no_db_write(self, monkeypatch):
        def _boom(*_a, **_k):  # pragma: no cover
            raise AssertionError("update не має викликатись")

        monkeypatch.setattr(contract_numbering.ProjectRepository, "update", _boom)
        data = {"invoice_number": "Р-20260101-009"}
        assert (
            contract_numbering.ensure_document_number(1, data, "invoice_number") == "Р-20260101-009"
        )

    def test_sequences_independent_per_document_type(self, monkeypatch):
        """Договір і рахунок того самого дня мають незалежні послідовності."""
        import re

        taken = {
            "contract_number": ["ДГ-20990101-005"],
            "invoice_number": ["Р-20990101-003"],
        }
        monkeypatch.setattr(
            contract_numbering,
            "_taken_numbers",
            lambda key: taken[key],
        )
        monkeypatch.setattr(
            contract_numbering.ProjectRepository,
            "update",
            staticmethod(lambda pid, data: {"id": pid}),
        )
        contract = contract_numbering.ensure_document_number(1, {}, "contract_number")
        invoice = contract_numbering.ensure_document_number(1, {}, "invoice_number")
        assert re.fullmatch(r"ДГ-\d{8}-001", contract)
        assert re.fullmatch(r"Р-\d{8}-001", invoice)
