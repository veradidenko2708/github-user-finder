import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
import threading
import re
from datetime import datetime

class GitHubUserFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Файл для избранных
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        self.current_user = None
        
        # API rate limiting информация
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        
        # Создание интерфейса
        self.create_widgets()
        self.refresh_favorites_list()
        
        # Проверка API статуса при запуске
        self.check_api_status()
    
    def validate_github_username(self, username):
        """
        Валидация имени пользователя GitHub
        Допустимые символы: буквы, цифры, дефис (не может начинаться или заканчиваться дефисом)
        """
        # Удаляем пробелы в начале и конце
        username = username.strip()
        
        # Проверка на пустоту
        if not username:
            return False, "Имя пользователя не может быть пустым"
        
        # Проверка длины (макс 39 символов)
        if len(username) > 39:
            return False, "Имя пользователя не может быть длиннее 39 символов"
        
        # Проверка минимальной длины
        if len(username) < 2:
            return False, "Имя пользователя должно содержать минимум 2 символа"
        
        # Проверка допустимых символов (буквы, цифры, дефис)
        if not re.match(r'^[a-zA-Z0-9-]+$', username):
            return False, "Имя пользователя может содержать только буквы, цифры и дефис"
        
        # Проверка: не может начинаться или заканчиваться дефисом
        if username.startswith('-') or username.endswith('-'):
            return False, "Имя пользователя не может начинаться или заканчиваться дефисом"
        
        # Проверка: не может содержать два дефиса подряд
        if '--' in username:
            return False, "Имя пользователя не может содержать два дефиса подряд"
        
        return True, "OK"
    
    def check_api_status(self):
        """Проверка статуса GitHub API и лимитов"""
        try:
            url = "https://api.github.com/rate_limit"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.rate_limit_remaining = data['rate']['remaining']
                self.rate_limit_reset = data['rate']['reset']
                
                if self.rate_limit_remaining < 10:
                    reset_time = datetime.fromtimestamp(self.rate_limit_reset)
                    self.status_bar.config(
                        text=f"Внимание: Осталось мало запросов API ({self.rate_limit_remaining}). Сброс в {reset_time.strftime('%H:%M:%S')}",
                        fg="orange"
                    )
                else:
                    self.status_bar.config(
                        text=f" Готов к работе | Доступно запросов: {self.rate_limit_remaining}",
                        fg="green"
                    )
        except Exception as e:
            self.status_bar.config(text=" Не удалось проверить статус API", fg="orange")
    
    def create_widgets(self):
        # Верхняя панель поиска
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(search_frame, text="Поиск пользователя GitHub:", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.search_entry = tk.Entry(search_frame, font=("Arial", 11), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda event: self.search_user())
        
        # Добавляем подсказку
        self.search_entry.insert(0, "например: octocat")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "например: octocat" else None)
        
        self.search_button = tk.Button(search_frame, text="🔍 Найти", command=self.search_user, 
                                      bg="#4CAF50", fg="white", font=("Arial", 10), padx=15)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Кнопка проверки статуса API
        api_status_btn = tk.Button(search_frame, text="📊 Статус API", command=self.check_api_status,
                                   bg="#607D8B", fg="white", font=("Arial", 9), padx=10)
        api_status_btn.pack(side=tk.LEFT, padx=5)
        
        # Разделительная панель
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ЛЕВАЯ ПАНЕЛЬ - результаты поиска
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=480)
        
        tk.Label(left_frame, text="Результаты поиска", font=("Arial", 11, "bold"), fg="blue").pack(pady=5)
        
        # Текстовое поле для результатов
        self.result_text = tk.Text(left_frame, height=20, wrap=tk.WORD, font=("Arial", 10))
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(left_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        
        # Кнопка добавления в избранное
        self.add_button = tk.Button(left_frame, text=" Добавить в избранное", 
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
        
        self.view_btn = tk.Button(btn_frame, text="👁 Просмотреть", command=self.view_favorite,
                                  bg="#2196F3", fg="white", font=("Arial", 9), padx=5)
        self.view_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.remove_btn = tk.Button(btn_frame, text="🗑 Удалить", command=self.remove_from_favorites,
                                    bg="#f44336", fg="white", font=("Arial", 9), padx=5)
        self.remove_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Статус бар
        self.status_bar = tk.Label(self.root, text=" Готов к работе", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Нижняя панель с кнопками
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=5, fill=tk.X)
        
        refresh_btn = tk.Button(bottom_frame, text="🔄 Обновить список избранных", command=self.refresh_favorites_list,
                                bg="#9E9E9E", fg="white", font=("Arial", 9))
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        clear_cache_btn = tk.Button(bottom_frame, text="🗑 Очистить кэш", command=self.clear_cache,
                                    bg="#FF5722", fg="white", font=("Arial", 9))
        clear_cache_btn.pack(side=tk.LEFT, padx=5)
    
    def search_user(self):
        username_raw = self.search_entry.get()
        
        # ВАЛИДАЦИЯ: проверка на пустое поле и значения по умолчанию
        if username_raw == "например: octocat":
            username_raw = ""
        
        # ВАЛИДАЦИЯ: проверка имени пользователя
        is_valid, error_message = self.validate_github_username(username_raw)
        
        if not is_valid:
            messagebox.showwarning("Ошибка ввода", error_message)
            self.status_bar.config(text=f" Ошибка: {error_message}", fg="red")
            return
        
        username = username_raw.strip()
        self.status_bar.config(text=f"🔍 Поиск пользователя '{username}'...", fg="blue")
        self.search_button.config(state=tk.DISABLED, text="Поиск...")
        
        # Запуск в отдельном потоке
        thread = threading.Thread(target=self._search_thread, args=(username,))
        thread.daemon = True
        thread.start()
    
    def _search_thread(self, username):
        try:
            url = f"https://api.github.com/users/{username}"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'GitHub-User-Finder-App'
            }
            response = requests.get(url, timeout=10, headers=headers)
            
            # Получение информации о rate limiting
            remaining = response.headers.get('X-RateLimit-Remaining')
            reset_time = response.headers.get('X-RateLimit-Reset')
            
            if remaining:
                self.rate_limit_remaining = int(remaining)
                self.rate_limit_reset = int(reset_time) if reset_time else None
            
            # Обработка различных статусов ответа
            if response.status_code == 200:
                user_data = response.json()
                self.root.after(0, self._show_user_info, user_data)
                self.root.after(0, self.status_bar.config, {'text': f" Найден пользователь: {username}", 'fg': 'green'})
                
            elif response.status_code == 404:
                self.root.after(0, self._show_error, f"Пользователь '{username}' не найден на GitHub")
                self.root.after(0, self.status_bar.config, {'text': " Пользователь не найден", 'fg': 'red'})
                
            elif response.status_code == 403:
                # Проверка на rate limiting
                if remaining and int(remaining) == 0:
                    reset_datetime = datetime.fromtimestamp(int(reset_time)) if reset_time else None
                    error_msg = f"Превышен лимит запросов к API"
                    if reset_datetime:
                        error_msg += f". Сброс в {reset_datetime.strftime('%H:%M:%S')}"
                    self.root.after(0, self._show_error, error_msg)
                    self.root.after(0, self.status_bar.config, {'text': " Превышен лимит запросов API", 'fg': 'orange'})
                else:
                    self.root.after(0, self._show_error, "Доступ запрещён. Возможно, требуется аутентификация")
                    self.root.after(0, self.status_bar.config, {'text': " Ошибка доступа", 'fg': 'red'})
                    
            else:
                self.root.after(0, self._show_error, f"Ошибка API: код {response.status_code}")
                self.root.after(0, self.status_bar.config, {'text': f" Ошибка API: {response.status_code}", 'fg': 'red'})
                
        except requests.exceptions.Timeout:
            self.root.after(0, self._show_error, "Превышено время ожидания. Проверьте интернет-соединение.")
            self.root.after(0, self.status_bar.config, {'text': " Таймаут соединения", 'fg': 'red'})
            
        except requests.exceptions.ConnectionError:
            self.root.after(0, self._show_error, "Нет подключения к интернету")
            self.root.after(0, self.status_bar.config, {'text': " Нет интернет-соединения", 'fg': 'red'})
            
        except Exception as e:
            self.root.after(0, self._show_error, f"Ошибка: {str(e)}")
            self.root.after(0, self.status_bar.config, {'text': f" Ошибка: {str(e)[:50]}", 'fg': 'red'})
            
        finally:
            self.root.after(0, lambda: self.search_button.config(state=tk.NORMAL, text="🔍 Найти"))
            # Обновляем информацию о лимитах в статус баре
            if self.rate_limit_remaining is not None:
                self.root.after(0, lambda: self.status_bar.config(
                    text=self.status_bar.cget("text") + f" | Осталось запросов: {self.rate_limit_remaining}"
                ))
    
    def _show_user_info(self, user):
        self.current_user = user
        self.result_text.delete(1.0, tk.END)
        
        # Проверяем, есть ли пользователь в избранном
        is_favorite = user['login'] in self.favorites
        fav_status = " В ИЗБРАННОМ" if is_favorite else "○ НЕ В ИЗБРАННОМ"
        
        info = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                         ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ                    ║
╚══════════════════════════════════════════════════════════════════════╝

{fav_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Логин:           {user.get('login', 'N/A')}
Имя:             {user.get('name', 'Не указано')}
Биография:       {user.get('bio', 'Не указана')}
Локация:         {user.get('location', 'Не указана')}
Компания:        {user.get('company', 'Не указана')}
Email:           {user.get('email', 'Не указан')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Репозитории:     {user.get('public_repos', 0)}
Подписчики:      {user.get('followers', 0)}
Подписки:        {user.get('following', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Дата регистрации: {user.get('created_at', 'N/A')[:10]}
Профиль:          {user.get('html_url', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self.result_text.insert(1.0, info)
    
    def _show_error(self, message):
        self.result_text.delete(1.0, tk.END)
        error_msg = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                             ОШИБКА                                   ║
╚══════════════════════════════════════════════════════════════════════╝

{message}

Возможные решения:
• Проверьте правильность написания имени пользователя
• Проверьте подключение к интернету
• Подождите несколько минут (при превышении лимита запросов)
• Попробуйте позже, если API GitHub недоступно
"""
        self.result_text.insert(1.0, error_msg)
    
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
        self.status_bar.config(text=f" {username} добавлен в избранное", fg="green")
        messagebox.showinfo("Успех", f"Пользователь '{username}' добавлен в избранное!")
        
        # Обновляем отображение информации (убираем статус "не в избранном")
        if self.current_user and self.current_user['login'] == username:
            self._show_user_info(self.current_user)
    
    def refresh_favorites_list(self):
        self.favorites_listbox.delete(0, tk.END)
        if not self.favorites:
            self.favorites_listbox.insert(tk.END, "── Список пуст ──")
        else:
            for username in sorted(self.favorites.keys()):
                self.favorites_listbox.insert(tk.END, f" {username}")
    
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
        
        username = self.favorites_listbox.get(self.selected_favorite_index).replace(" ", "")
        
        if username in self.favorites:
            self._show_user_info(self.favorites[username])
            self.current_user = self.favorites[username]
            self.status_bar.config(text=f"👁 Просмотр избранного: {username}", fg="blue")
    
    def remove_from_favorites(self):
        if not hasattr(self, 'selected_favorite_index'):
            messagebox.showwarning("Ошибка", "Выберите пользователя из списка!")
            return
        
        if not self.favorites:
            return
        
        username = self.favorites_listbox.get(self.selected_favorite_index).replace(" ", "")
        
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{username}' из избранного?"):
            del self.favorites[username]
            self.save_favorites()
            self.refresh_favorites_list()
            self.status_bar.config(text=f"🗑 {username} удалён из избранного", fg="orange")
            
            # Сброс выбора
            if hasattr(self, 'selected_favorite_index'):
                delattr(self, 'selected_favorite_index')
    
    def clear_cache(self):
        """Очистка кэша и перезагрузка"""
        if messagebox.askyesno("Подтверждение", "Очистить кэш и сбросить все данные?\n(Избранные останутся сохранёнными)"):
            self.result_text.delete(1.0, tk.END)
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, "например: octocat")
            self.current_user = None
            self.status_bar.config(text=" Кэш очищен", fg="green")
            self.check_api_status()
    
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
