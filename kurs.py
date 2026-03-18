import tkinter as tk
import requests
from bs4 import BeautifulSoup
import threading
import time
import json
import os

CONFIG_FILE = "widget_config.json"

class CurrencyApp:
    def __init__(self):
        self.config = self.load_config()
        self.root = tk.Tk()
        
        # Налаштування вікна: без рамок, завжди зверху
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Встановлюємо збережену позицію або дефолтну (правій нижній кут)
        pos = self.config.get("position", "+1500+1010")
        self.root.geometry(f"180x35{pos}")
        self.root.configure(bg='#1e1e1e') # Колір під темну тему Windows

        self.rates = {"USD": "...", "EUR": "...", "PLN": "..."}
        self.current_main = self.config.get("main_currency", "USD")

        # Основний текст
        self.label = tk.Label(self.root, text="Завантаження...", fg="#ffffff", 
                              bg="#1e1e1e", font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.label.pack(expand=True, fill="both")

        # Спливаюче вікно (EUR/PLN)
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

        # Запуск фонового потоку
        threading.Thread(target=self.data_loop, daemon=True).start()
        
        # Метод для постійної перевірки "topmost" стану
        self.keep_on_top()
        
        self.root.mainloop()

    def keep_on_top(self):
        """Примусово тримає вікно поверх усіх інших кожні 2 секунди"""
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.after(2000, self.keep_on_top)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_current_config(self, event=None):
        self.config["position"] = f"+{self.root.winfo_x()}+{self.root.winfo_y()}"
        self.config["main_currency"] = self.current_main
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def get_data(self):
        url = "https://lion-kurs.rv.ua/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8' 
            soup = BeautifulSoup(res.text, 'html.parser')
            new_rates = {}

            # Мапінг по іконках прапорів
            mapping = {"usd.gif": "USD", "eur.gif": "EUR", "pol.gif": "PLN"}

            rows = soup.find_all('tr')
            for row in rows:
                img = row.find('img')
                if img and img.get('src'):
                    src = img.get('src').split('/')[-1]
                    if src in mapping:
                        cols = row.find_all('td', class_='white')
                        if len(cols) >= 2:
                            buy = cols[0].get_text(strip=True)
                            sell = cols[1].get_text(strip=True)
                            new_rates[mapping[src]] = f"{buy} / {sell}"
            return new_rates if len(new_rates) > 0 else None
        except:
            return None

    def perform_update(self):
        data = self.get_data()
        if data:
            self.rates.update(data)
            self.label.config(text=f"{self.current_main}: {self.rates[self.current_main]}")
        else:
            self.label.config(text="Помилка оновлення")

    def data_loop(self):
        while True:
            self.perform_update()
            time.sleep(3600) # Оновлення кожну годину

    def show_popup(self, event):
        others = [f"{k}: {v}" for k, v in self.rates.items() if k != self.current_main]
        self.pop_label.config(text="\n".join(others))
        # Позиція вікна над віджетом
        self.popup.geometry(f"+{self.root.winfo_x()}+{self.root.winfo_y() - 65}")
        self.popup.deiconify()

    def hide_popup(self, event):
        self.popup.withdraw()

    def move_window(self, event):
        self.root.geometry(f"+{event.x_root-50}+{event.y_root-15}")

    def show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="🔄 Оновити зараз", command=self.perform_update)
        menu.add_separator()
        for cur in ["USD", "EUR", "PLN"]:
            menu.add_command(label=f"Показувати {cur}", command=lambda c=cur: self.set_currency(c))
        menu.add_separator()
        menu.add_command(label="Вихід", command=self.root.destroy)
        menu.post(event.x_root, event.y_root)

    def set_currency(self, cur):
        self.current_main = cur
        self.perform_update()
        self.save_current_config()

if __name__ == "__main__":
    CurrencyApp()