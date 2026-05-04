import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
import threading

class GitHubUserFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("850x650")
        self.root.resizable(True, True)
        
        # Файл для избранных
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        self.current_user = None
        
        # Создание интерфейса
        self.create_widgets()
        self.refresh_favorites_list()
    
    def create_widgets(self):
        # Верхняя панель поиска
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(search_frame, text="Поиск пользователя GitHub:", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.search_entry = tk.Entry(search_frame, font=("Arial", 11), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda event: self.search_user())
        
        self.search_button = tk.Button(search_frame, text=" Найти", command=self.search_user, 
                                      bg="#4CAF50", fg="white", font=("Arial", 10), padx=15)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Разделительная панель
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ЛЕВАЯ ПАНЕЛЬ - результаты поиска
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=450)
        
        tk.Label(left_frame, text="Результаты поиска", font=("Arial", 11, "bold"), fg="blue").pack(pady=5)
        
        # Текстовое поле для результатов
        self.result_text = tk.Text(left_frame, height=18, wrap=tk.WORD, font=("Arial", 10))
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(left_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        
        # Кнопка добавления в избранное
        self.add_button = tk.Button(left_frame, text="⭐ Добавить в избранное", 
                                    command=self.add_to_favorites,
                                    bg="#FFC107", font=("Arial", 10, "bold"), padx=10, pady=5)
        self.add_button.pack(pady=10)
        
        # ПРАВАЯ ПАНЕЛЬ - избранные
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, width=350)
        
        tk.Label(right_frame, text="Избранные пользователи", font=("Arial", 11, "bold"), fg="green").pack(pady=5)
        
        # Список избранных
        self.favorites_listbox = tk.Listbox(right_frame, font=("Arial", 10), height=15)
        self.favorites_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        fav_scrollbar = tk.Scrollbar(right_frame, command=self.favorites_listbox.yview)
        fav_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.favorites_listbox.config(yscrollcommand=fav_scrollbar.set)
        
        self.favorites_listbox.bind("<<ListboxSelect>>", self.on_favorite_select)
        
        # Кнопки управления избранными
        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        self.view_btn = tk.Button(btn_frame, text=" Просмотреть", command=self.view_favorite,
                                  bg="#2196F3", fg="white", font=("Arial", 9), padx=5)
        self.view_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.remove_btn = tk.Button(btn_frame, text=" Удалить", command=self.remove_from_favorites,
                                    bg="#f44336", fg="white", font=("Arial", 9), padx=5)
        self.remove_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Статус бар
        self.status_bar = tk.Label(self.root, text=" Готов к работе", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Кнопка обновления
        refresh_btn = tk.Button(self.root, text=" Обновить список избранных", command=self.refresh_favorites_list,
                                bg="#9E9E9E", fg="white", font=("Arial", 9))
        refresh_btn.pack(pady=5)
    
    def search_user(self):
        username = self.search_entry.get().strip()
        
        # ВАЛИДАЦИЯ: проверка на пустое поле
        if not username:
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, введите имя пользователя!")
            self.status_bar.config(text=" Ошибка: пустое поле поиска")
            return
        
        # ВАЛИДАЦИЯ: проверка длины имени
        if len(username) > 39:
            messagebox.showwarning("Ошибка ввода", "Имя пользователя не может быть длиннее 39 символов!")
            self.status_bar.config(text=" Ошибка: слишком длинное имя")
            return
        
        self.status_bar.config(text=f" Поиск пользователя '{username}'...")
        self.search_button.config(state=tk.DISABLED, text="Поиск...")
        
        # Запуск в отдельном потоке
        thread = threading.Thread(target=self._search_thread, args=(username,))
        thread.daemon = True
        thread.start()
    
    def _search_thread(self, username):
        try:
            url = f"https://api.github.com/users/{username}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                self.root.after(0, self._show_user_info, user_data)
                self.root.after(0, self.status_bar.config, {'text': f" Найден пользователь: {username}"})
            elif response.status_code == 404:
                self.root.after(0, self._show_error, f"Пользователь '{username}' не найден")
                self.root.after(0, self.status_bar.config, {'text': " Пользователь не найден"})
            else:
                self.root.after(0, self._show_error, f"Ошибка API: код {response.status_code}")
                self.root.after(0, self.status_bar.config, {'text': " Ошибка при запросе"})
        except requests.exceptions.Timeout:
            self.root.after(0, self._show_error, "Превышено время ожидания. Проверьте интернет-соединение.")
        except requests.exceptions.ConnectionError:
            self.root.after(0, self._show_error, "Нет подключения к интернету")
        except Exception as e:
            self.root.after(0, self._show_error, f"Ошибка: {str(e)}")
        finally:
            self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL, text="🔍 Найти"))
    
    def _show_user_info(self, user):
        self.current_user = user
        self.result_text.delete(1.0, tk.END)
        
        info = f"""
╔══════════════════════════════════════════════════════════════╗
║                      ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ               ║
╚══════════════════════════════════════════════════════════════╝

 Логин: {user.get('login', 'N/A')}
 Имя: {user.get('name', 'Не указано')}
 Биография: {user.get('bio', 'Не указана')}
 Локация: {user.get('location', 'Не указана')}
 Компания: {user.get('company', 'Не указана')}
 Email: {user.get('email', 'Не указан')}
 Дата регистрации: {user.get('created_at', 'N/A')[:10]}
 Публичные репозитории: {user.get('public_repos', 0)}
 Подписчики: {user.get('followers', 0)}
 Подписки: {user.get('following', 0)}
 Профиль: {user.get('html_url', 'N/A')}
        """
        self.result_text.insert(1.0, info)
    
    def _show_error(self, message):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, f"❌ ОШИБКА:\n\n{message}")
    
    def add_to_favorites(self):
        if self.current_user is None:
            messagebox.showwarning("Ошибка", "Сначала найдите пользователя!")
            return
        
        username = self.current_user['login']
        
        if username in self.favorites:
            messagebox.showinfo("Информация", f"Пользователь '{username}' уже в избранном!")
            return
        
        self.favorites[username] = self.current_user
        self.save_favorites()
        self.refresh_favorites_list()
        self.status_bar.config(text=f"⭐ {username} добавлен в избранное")
        messagebox.showinfo("Успех", f"Пользователь '{username}' добавлен в избранное!")
    
    def refresh_favorites_list(self):
        self.favorites_listbox.delete(0, tk.END)
        if not self.favorites:
            self.favorites_listbox.insert(tk.END, "── Список пуст ──")
        else:
            for username in sorted(self.favorites.keys()):
                self.favorites_listbox.insert(tk.END, f"⭐ {username}")
    
    def on_favorite_select(self, event):
        selection = self.favorites_listbox.curselection()
        if selection and self.favorites:
            self.selected_favorite_index = selection[0]
    
    def view_favorite(self):
        if not hasattr(self, 'selected_favorite_index'):
            messagebox.showwarning("Ошибка", "Выберите пользователя из списка!")
            return
        
        if not self.favorites:
            return
        
        username = self.favorites_listbox.get(self.selected_favorite_index).replace("⭐ ", "")
        
        if username in self.favorites:
            self._show_user_info(self.favorites[username])
            self.status_bar.config(text=f"👁 Просмотр избранного: {username}")
    
    def remove_from_favorites(self):
        if not hasattr(self, 'selected_favorite_index'):
            messagebox.showwarning("Ошибка", "Выберите пользователя из списка!")
            return
        
        if not self.favorites:
            return
        
        username = self.favorites_listbox.get(self.selected_favorite_index).replace("⭐ ", "")
        
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{username}' из избранного?"):
            del self.favorites[username]
            self.save_favorites()
            self.refresh_favorites_list()
            self.status_bar.config(text=f" {username} удалён из избранного")
            
            # Сброс выбора
            if hasattr(self, 'selected_favorite_index'):
                delattr(self, 'selected_favorite_index')
    
    def load_favorites(self):
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except (json.JSONDecodeError, Exception):
            return {}
    
    def save_favorites(self):
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubUserFinder(root)
    root.mainloop()