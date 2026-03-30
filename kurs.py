import winsound
import tkinter as tk
from tkinter import Menu, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import time
import json
import os
import logging
from datetime import datetime

# --- КОНФІГУРАЦІЯ ---
CONFIG_FILE = "widget_config.json"
LOG_FILENAME = "kurs_history.log"

# Налаштування логів
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

class CurrencyApp:
    def __init__(self):
        self.config = self.load_config()
        self.root = tk.Tk()
        
        # Налаштування вікна
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.wm_attributes("-toolwindow", True)
        
        pos = self.config.get("position", "+1500+1010")
        self.root.geometry(f"180x35{pos}")
        self.root.configure(bg='#1e1e1e')

        self.rates = {"USD": "...", "EUR": "...", "PLN": "..."}
        self.current_main = self.config.get("main_currency", "USD")

        # Інтерфейс
        self.label = tk.Label(self.root, text="Завантаження...", fg="#ffffff", 
                              bg="#1e1e1e", font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.label.pack(expand=True, fill="both")

        # Popup
        self.popup = tk.Toplevel(self.root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(bg='#2d2d2d')
        self.popup.withdraw()

        self.pop_label = tk.Label(self.popup, text="", fg="white", bg="#2d2d2d", 
                                  font=("Segoe UI", 9), justify="left", padx=10, pady=5)
        self.pop_label.pack()

        # Прив'язка подій
        self.label.bind("<Enter>", self.show_popup)
        self.label.bind("<Leave>", self.hide_popup)
        self.label.bind("<B1-Motion>", self.move_window)
        self.label.bind("<ButtonRelease-1>", self.save_current_config)
        self.label.bind("<Button-3>", self.show_menu)

        # Потоки
        threading.Thread(target=self.data_loop, daemon=True).start()
        self.keep_on_top()
        
        self.root.mainloop()

    def get_data(self):
        url = "https://lion-kurs.rv.ua/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8' 
            soup = BeautifulSoup(res.text, 'html.parser')
            new_rates = {}

            # ВАШ ПЕРЕВІРЕНИЙ МАПІНГ
            mapping = {"usd.gif": "USD", "eur.gif": "EUR", "pol.gif": "PLN"}

            rows = soup.find_all('tr')
            for row in rows:
                img = row.find('img')
                if img and img.get('src'):
                    src = img.get('src').split('/')[-1]
                    if src in mapping:
                        # Шукаємо саме ті колонки, що були у вас
                        cols = row.find_all('td', class_='white')
                        if len(cols) >= 2:
                            buy = cols[0].get_text(strip=True)
                            sell = cols[1].get_text(strip=True)
                            new_rates[mapping[src]] = f"{buy} / {sell}"
            return new_rates if len(new_rates) > 0 else None
        except:
            return None

    def perform_update(self):
        raw_old = self.rates.get(self.current_main, "0").split(' / ')[0]
        try:
            old_val = float(raw_old.replace(',', '.'))
        except:
            old_val = 0.0

        data = self.get_data()
        if data:
            new_raw = data.get(self.current_main, "0").split(' / ')[0]
            try:
                new_val = float(new_raw.replace(',', '.'))
                diff = abs(new_val - old_val)

                if old_val != 0 and new_val != old_val:
                    # Визначаємо тренд для логів
                    trend = "ВГОРУ" if new_val > old_val else "ВНИЗ"
                    self.label.config(fg="#00ff00" if new_val > old_val else "#ff4d4d")

                    # ЗАПИС У ЛОГ
                    logging.info(f"{self.current_main}: {old_val:.2f} -> {new_val:.2f} ({trend})")

                    if diff >= 0.10:
                        winsound.Beep(1000, 500) 
                else:
                    self.label.config(fg="#ffffff")

            except:
                self.label.config(fg="#ffffff")

            self.rates.update(data)
            self.label.config(text=f"{self.current_main}: {self.rates[self.current_main]}")
        else:
            self.label.config(text="Помилка мережі", fg="orange")

    # --- ФУНКЦІЯ ГРАФІКА ---
    def show_chart(self):
        threading.Thread(target=self._plot_thread, daemon=True).start()

    def _plot_thread(self):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            if not os.path.exists(LOG_FILENAME):
                messagebox.showinfo("Lion Kurs", "Лог порожній.")
                return

            times, vals = [], []
            with open(LOG_FILENAME, 'r', encoding='utf-8') as f:
                for line in f:
                    if f"- {self.current_main}:" in line:
                        try:
                            parts = line.split(' - ')
                            dt = datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S')
                            v = float(parts[1].split(' -> ')[1].split(' ')[0].replace(',', '.'))
                            times.append(dt)
                            vals.append(v)
                        except: continue

            if len(times) < 2:
                messagebox.showinfo("Lion Kurs", "Треба хоча б 2 зміни курсу в логах.")
                return

            plt.figure(figsize=(8, 4))
            plt.plot(times, vals, marker='o', color='#0057b8')
            plt.title(f"Історія {self.current_main}")
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.gcf().autofmt_xdate()
            plt.grid(True, alpha=0.3)
            plt.show()
        except ImportError:
            messagebox.showerror("Помилка", "Встановіть matplotlib: pip install matplotlib")

    # --- СТАНДАРТНІ МЕТОДИ ---
    def keep_on_top(self):
        self.root.attributes("-topmost", True)
        self.root.after(2000, self.keep_on_top)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: return json.load(f)
            except: pass
        return {}

    def save_current_config(self, event=None):
        self.config["position"] = f"+{self.root.winfo_x()}+{self.root.winfo_y()}"
        self.config["main_currency"] = self.current_main
        with open(CONFIG_FILE, "w") as f: json.dump(self.config, f)

    def data_loop(self):
        while True:
            self.perform_update()
            time.sleep(3600)

    def show_popup(self, event):
        others = [f"{k}: {v}" for k, v in self.rates.items() if k != self.current_main]
        self.pop_label.config(text="\n".join(others))
        self.popup.geometry(f"+{self.root.winfo_x()}+{self.root.winfo_y() - 65}")
        self.popup.deiconify()

    def hide_popup(self, event):
        self.popup.withdraw()

    def move_window(self, event):
        self.root.geometry(f"+{event.x_root-50}+{event.y_root-15}")

    def show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="🔄 Оновити зараз", command=self.perform_update)
        menu.add_command(label="📈 Графік змін", command=self.show_chart)
        menu.add_separator()
        for cur in ["USD", "EUR", "PLN"]:
            menu.add_command(label=f"Показувати {cur}", command=lambda c=cur: self.set_currency(c))
        menu.add_separator()
        menu.add_command(label="Вихід", command=self.root.destroy)
        menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    CurrencyApp()