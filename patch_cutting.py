import sys

f = open(sys.argv[1], encoding='utf-8')
lines = f.readlines()
f.close()

new = []
for i, line in enumerate(lines):
    if i == 125:  # рядок 126 (0-based = 125)
        new.append('    def _calculate(self):\n')
        new.append('        try:\n')
        new.append('            products = self.get_products()\n')
        new.append('            print(f"[DEBUG] Отримано {len(products) if products else 0} виробів для розкрою")\n')
        new.append('            if hasattr(self, "get_standard_products") and self.get_standard_products:\n')
        new.append('                sp = self.get_standard_products()\n')
        new.append('                print(f"[DEBUG] StandardProducts: {len(sp) if sp else 0}")\n')
        new.append('            self.run_cutting_for_products(products)\n')
        new.append('        except Exception as e:\n')
        new.append('            import traceback\n')
        new.append('            err = traceback.format_exc()\n')
        new.append('            print(f"[DEBUG] ПОМИЛКА в _calculate: {err}")\n')
        new.append('            messagebox.showerror("Помилка", f"Помилка отримання виробів:\n{str(e)}\n\nДеталі в консолі.")\n')
    elif i == 126 or i == 127:
        continue
    else:
        new.append(line)

f = open(sys.argv[1], 'w', encoding='utf-8')
f.writelines(new)
f.close()
print('done')
