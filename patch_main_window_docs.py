# -*- coding: utf-8 -*-
"""Patch: adds Documents tab to main_window.py

Run: python patch_main_window_docs.py
"""

FILE_PATH = "ventilation_company/gui_pyside6/main_window.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
old_imp = "from ventilation_company.gui_pyside6.crm_tab import CRMTab"
new_imp = old_imp + "\nfrom ventilation_company.gui_pyside6.documents_tab import DocumentsTab"
if old_imp in content:
    content = content.replace(old_imp, new_imp)
    print("Import added.")
else:
    print("WARN: import not found.")

# 2. Add to tabs dict
old_tabs = '"crm": CRMTab(self, main_window=self),'
new_tabs = '"crm": CRMTab(self, main_window=self),\n            "documents": DocumentsTab(self, main_window=self),'
if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    print("Tab added to dict.")
else:
    print("WARN: tabs dict not found.")

# 3. Add to sidebar
old_side = '("crm", "👥 CRM"),'
new_side = '("crm", "👥 CRM"),\n            ("documents", "📄 Документи"),'
if old_side in content:
    content = content.replace(old_side, new_side)
    print("Sidebar item added.")
else:
    print("WARN: sidebar not found.")

# 4. Add refresh in tab_changed
old_change = 'elif name == "crm":'
new_change = 'elif name == "documents":\n                self.tabs[name].refresh()\n            elif name == "crm":'
if old_change in content:
    content = content.replace(old_change, new_change)
    print("Tab refresh added.")
else:
    print("WARN: tab_changed not found.")

# 5. Add sync in set_active_project
old_active = 'elif name == "specification":'
if old_active in content:
    # Replace first occurrence only
    content = content.replace(old_active, 'elif name == "specification":\n                widget.on_project_changed(project_id)\n            elif name == "documents":\n                widget.on_project_changed(project_id)\n            elif name == "specification":', 1)
    print("Active project sync added.")
else:
    print("WARN: set_active_project not found.")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Restart: python main_pyside6.py")
