"""
Патч для settings_tab.py — додає метод _build_waste_tab
"""
import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    # Додаємо _build_waste_tab перед _reset_defaults
    if 'def _reset_defaults(self):' in line:
        new.append("    def _build_waste_tab(self):\n")
        new.append('        """Вкладка коефіцієнтів запасу на брак/поворот по категоріях."""\n')
        new.append("        top = ttk.Frame(self.waste_frame, padding=5)\n")
        new.append("        top.pack(fill=tk.X)\n")
        new.append('        ttk.Label(top, text="📦 Коефіцієнти запасу на брак/поворот (%)", font=("Arial", 12, "bold")).pack(side=tk.LEFT)\n')
        new.append('        ttk.Button(top, text="💾 Зберегти", command=self._save_waste_factors).pack(side=tk.RIGHT, padx=5)\n')
        new.append("\n")
        new.append('        frame = ttk.LabelFrame(self.waste_frame, text="Налаштування коефіцієнтів по категоріях", padding=10)\n')
        new.append("        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)\n")
        new.append("\n")
        new.append('        self.waste_vars = {}\n')
        new.append("        categories = [\n")
        new.append('            ("rect_duct", "Прямокутні труби (повітропроводи)"),\n')
        new.append('            ("rect_fitting", "Прямокутні фасонні вироби (фланці, трійники, відводи...)"),\n')
        new.append('            ("round_duct", "Круглі труби (повітропроводи)"),\n')
        new.append('            ("round_fitting", "Круглі фасонні вироби (фланці, трійники, відводи...)"),\n')
        new.append("        ]\n")
        new.append("        for i, (key, label) in enumerate(categories):\n")
        new.append('            ttk.Label(frame, text=label, font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=8, padx=5)\n')
        new.append('            var = tk.StringVar(value=str(self.settings.category_waste_factors.get(key, 0.0)))\n')
        new.append('            ent = ttk.Entry(frame, textvariable=var, width=10)\n')
        new.append('            ent.grid(row=i, column=1, padx=5, pady=8, sticky=tk.W)\n')
        new.append('            ttk.Label(frame, text="%").grid(row=i, column=2, sticky=tk.W, pady=8)\n')
        new.append('            self.waste_vars[key] = var\n')
        new.append("\n")
        new.append("        help_text = (\n")
        new.append('            "💡 Коефіцієнт запасу додається до вартості матеріалу:\\n"\n')
        new.append('            "   Вартість матеріалу × (1 + коефіцієнт_категорії / 100)\\n\\n"\n')
        new.append('            "Приклад: якщо коефіцієнт = 5%, то вартість металу\\n"\n')
        new.append('            "збільшується на 5% для відповідної категорії виробів."\n')
        new.append("        )\n")
        new.append('        ttk.Label(frame, text=help_text, foreground=self._fg("fg_muted"),\n')
        new.append('                justify=tk.LEFT, font=("Consolas", 9)).grid(row=len(categories), column=0,\n')
        new.append('                columnspan=3, sticky=tk.W, pady=15, padx=5)\n')
        new.append("\n")
        new.append("    def _save_waste_factors(self):\n")
        new.append('        """Зберегти коефіцієнти запасу."""\n')
        new.append("        try:\n")
        new.append("            for key, var in self.waste_vars.items():\n")
        new.append("                self.settings.category_waste_factors[key] = float(var.get())\n")
        new.append("            self.settings.save()\n")
        new.append('            messagebox.showinfo("Успіх", "Коефіцієнти запасу збережено!")\n')
        new.append("        except ValueError:\n")
        new.append('            messagebox.showwarning("Увага", "Усі значення мають бути числами.")\n')
        new.append("\n")
        new.append(line)
        continue
    
    new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
