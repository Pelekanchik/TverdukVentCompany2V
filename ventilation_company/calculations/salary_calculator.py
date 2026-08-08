"""Калькулятор зарплати з урахуванням податків."""

from ventilation_company.config import POSITIONS


class SalaryCalculator:
    """Розрахунок зарплати з ПДФО, військовим збором та ЄСВ."""

    PIT_RATE = 0.18
    MILITARY_TAX_RATE = 0.015
    ESV_RATE = 0.22

    def __init__(self):
        self.employees = []

    def add_employee(self, full_name: str, position: str):
        pos_data = POSITIONS.get(position, {"ставка": 0, "премія_%": 0})
        self.employees.append({
            "full_name": full_name,
            "position": position,
            "base_salary": pos_data["ставка"],
            "bonus_percent": pos_data["премія_%"],
        })

    def calculate_employee_net(self, gross_salary: float) -> dict:
        gross = float(gross_salary)
        pit = round(gross * self.PIT_RATE, 2)
        military_tax = round(gross * self.MILITARY_TAX_RATE, 2)
        net_salary = round(gross - pit - military_tax, 2)
        esv = round(gross * self.ESV_RATE, 2)
        return {
            "gross_salary": gross,
            "pit": pit,
            "military_tax": military_tax,
            "net_salary": net_salary,
            "esv": esv,
        }

    def calculate_payroll(self) -> dict:
        total_gross = 0.0
        total_net = 0.0
        total_esv = 0.0

        for emp in self.employees:
            gross = emp["base_salary"] * (1 + emp["bonus_percent"] / 100)
            tax_data = self.calculate_employee_net(gross)
            total_gross += gross
            total_net += tax_data["net_salary"]
            total_esv += tax_data["esv"]

        return {
            "employees_count": len(self.employees),
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_esv": round(total_esv, 2),
            "total_employer_cost": round(total_gross + total_esv, 2),
        }