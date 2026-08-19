"""
Патч для settings_tab.py — додає під-вкладку "Коефіцієнти запасу"
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо під-вкладку після markup_tab
    if 'self.notebook.add(self.markup_tab.frame, text="📐 Націнки по категоріях")' in line:
        new.append(line)
        new.append("\n")
        new.append("        self.waste_frame = ttk.Frame(self.notebook)\n")
        new.append('        self.notebook.add(self.waste_frame, text="📦 Коефіцієнти запасу")\n')
        new.append("        self._build_waste_tab()\n")
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
