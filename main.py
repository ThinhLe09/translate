import sys
import logging
import os
import threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

import webbrowser



# Cấu hình log ngay từ đầu
log_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "debug_log.txt")
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

import sys
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

def check_expiry_date():
    EXPIRY_DATE = datetime(2026, 5, 1)
    WARNING_DAYS = 7
    UPDATE_URL = "https://inside-docupedia.bosch.com/confluence2/spaces/NETFTVN/pages/1026127404/AI+Solution+maintain+NET-ECA"
    
    now = datetime.now()
    remaining = EXPIRY_DATE - now

    if now >= EXPIRY_DATE:
        popup = ctk.CTk()
        popup.title("Version Expired")
        ctk.set_appearance_mode("dark")
        
        # --- FIX KÍCH THƯỚC TẠI ĐÂY ---
        window_width = 600
        window_height = 300
        
        # Lấy độ phân giải màn hình
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        
        # Tính toán tọa độ x, y để căn giữa
        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))
        
        # Set chính xác kích thước và vị trí
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
        popup.resizable(False, False) # Khoá không cho kéo giãn

        # --- GIAO DIỆN ---
        lbl_icon = ctk.CTkLabel(popup, text="❌", font=("Arial", 40))
        lbl_icon.pack(pady=(15, 5))

        lbl_title = ctk.CTkLabel(popup, text=f"This version expired on {EXPIRY_DATE.strftime('%d/%m/%Y')}.", font=("Arial", 18, "bold"))
        lbl_title.pack()

        # wraplength=550 giúp chữ tự xuống dòng nếu chạm biên
        lbl_info = ctk.CTkLabel(popup, text="Please download the latest version to continue using the tool:", font=("Arial", 14), wraplength=550)
        lbl_info.pack(pady=(15, 5))

        def open_link(event):
            webbrowser.open_new(UPDATE_URL)

        link_font = ctk.CTkFont(family="Arial", size=13, underline=True)
        lbl_link = ctk.CTkLabel(popup, text="🔗 Click here to open Download Page (Inside Docupedia)", 
                                font=link_font, text_color="#3498db", cursor="hand2", wraplength=550)
        lbl_link.pack(pady=5)
        lbl_link.bind("<Button-1>", open_link)

        lbl_support = ctk.CTkLabel(popup, text="Support: (dab8hc | poa9hc | nmu3hc)@bosch.com", font=("Arial", 13), text_color="gray")
        lbl_support.pack(pady=(15, 15))

        def close_app():
            popup.destroy()
            sys.exit(1)

        btn_ok = ctk.CTkButton(popup, text="Close Application", command=close_app, fg_color="#c0392b", hover_color="#e74c3c", width=150)
        btn_ok.pack()

        popup.protocol("WM_DELETE_WINDOW", close_app)
        popup.mainloop()

    elif remaining.days <= WARNING_DAYS:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Update Reminder", 
            f"This version will expire in {remaining.days} days.\n"
            "Please plan to update soon!"
        )
        root.destroy()

# 2. APP CHÍNH & MÀN HÌNH LOADING
class TranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Tạm ẩn giao diện app chính ngay lập tức
        
        # --- DỰNG MÀN HÌNH CHỜ (SPLASH SCREEN) ---
        self.splash = ctk.CTkToplevel(self)
        self.splash.title("Loading")
        self.splash.geometry("350x150")
        self.splash.overrideredirect(True) # Ẩn thanh tiêu đề cho giống popup
        self.splash.attributes("-topmost", True)
        
        # Căn giữa màn hình chờ
        self.splash.update_idletasks()
        w = self.splash.winfo_width()
        h = self.splash.winfo_height()
        x = (self.splash.winfo_screenwidth() // 2) - (w // 2)
        y = (self.splash.winfo_screenheight() // 2) - (h // 2)
        self.splash.geometry(f'{w}x{h}+{x}+{y}')

        self.splash_label = ctk.CTkLabel(self.splash, text="Models loading...\nPlease wait!", font=("Arial", 14, "bold"))
        self.splash_label.pack(expand=True)
        self.progress = ctk.CTkProgressBar(self.splash, mode="indeterminate", width=250)
        self.progress.pack(pady=15)
        self.progress.start()

        # Bắt đầu gọi hàm load thư viện nặng sau 100ms (để UI popup kịp hiển thị)
        self.after(100, self.start_loading_models)

    def start_loading_models(self):
        # Chạy một luồng phụ để import module, tránh làm đơ thanh loading bar
        threading.Thread(target=self._import_heavy_modules, daemon=True).start()

    def _import_heavy_modules(self):
        # 3. IMPORT CÁC THƯ VIỆN NẶNG TẠI ĐÂY (Lazy Loading)
        global config, tracking, handle_excel, handle_word, handle_pdf, handle_raw
        from plugin import config       
        from plugin import tracking      
        from plugin import handle_excel 
        from plugin import handle_word   
        from plugin import handle_pdf   
        from plugin import handle_raw
        
        # Sau khi import xong hết, quay lại luồng chính để vẽ UI App
        self.after(0, self.setup_main_ui)

    def setup_main_ui(self):
        # Đóng màn hình chờ
        self.splash.destroy()
        
        # --- BẮT ĐẦU DỰNG GIAO DIỆN APP CHÍNH ---
        self.title("Bosch Multi-File Translator Tool")
        self.geometry("650x700")
        ctk.set_appearance_mode("dark")

        self.label_title = ctk.CTkLabel(self, text="Offline Translation System", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=15)

        self.entry_input = ctk.CTkEntry(self, placeholder_text="Input file path...", width=400)
        self.entry_input.pack(pady=5)
        self.btn_browse_in = ctk.CTkButton(self, text="Select File", command=self.browse_file)
        self.btn_browse_in.pack(pady=5)

        self.entry_output = ctk.CTkEntry(self, placeholder_text="Output folder...", width=400)
        self.entry_output.pack(pady=5)
        self.btn_browse_out = ctk.CTkButton(self, text="Select Output Folder", command=self.browse_output)
        self.btn_browse_out.pack(pady=5)

        self.label_lang = ctk.CTkLabel(self, text="Target Language:")
        self.label_lang.pack(pady=(10, 0))
        self.combo_lang = ctk.CTkComboBox(self, values=["English", "Vietnamese", "Chinese"])
        self.combo_lang.set("English")
        self.combo_lang.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)
        self.last_progress_percent = -1 

        self.cancel_event = threading.Event()

        self.btn_translate = ctk.CTkButton(self, text="Start Translation", command=self.start_translation_thread)
        self.btn_translate.pack(pady=5)

        self.btn_cancel = ctk.CTkButton(self, text="Cancel Translation", command=self.cancel_action, fg_color="#c0392b", hover_color="#e74c3c", state="disabled")
        self.btn_cancel.pack(pady=5)

        self.textbox_log = ctk.CTkTextbox(self, width=500, height=150, state="disabled")
        self.textbox_log.pack(pady=15)

        try:
            tracking.log_app_open(purpose="Translate files")
        except Exception as e:
            logging.warning(f"Tracking error: {e}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # --- HIỆN APP CHÍNH SAU KHI DỰNG XONG ---
        self.deiconify()

    # --- CÁC HÀM XỬ LÝ LOGIC UI GIỮ NGUYÊN ---
    def on_close(self):
        try:
            tracking.log_app_close()
        except Exception as e:
            logging.warning(f"Tracking error: {e}")
        self.destroy()

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.textbox_log.configure(state="normal")
        time_now = datetime.now().strftime("%H:%M:%S")
        self.textbox_log.insert("end", f"[{time_now}] {message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def update_progress(self, value):
        percent = int(value * 100)
        if percent != self.last_progress_percent:
            self.last_progress_percent = percent
            self.after(0, self._set_progress, value)

    def _set_progress(self, value):
        self.progress_bar.set(value)

    def browse_file(self):
        file_path = filedialog.askopenfilename(title="Select any file to translate", filetypes=[("All Files", "*.*")])
        if file_path:
            self.entry_input.delete(0, "end")
            self.entry_input.insert(0, file_path)
            default_output_dir = os.path.dirname(file_path)
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, default_output_dir)
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            self.log(f"Selected file: {os.path.basename(file_path)} ({file_size:.2f} MB)")

    def browse_output(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, dir_path)

    def cancel_action(self):
        if messagebox.askyesno("Yes", "Are you sure you want to cancel the translation?"):
            self.log("⏳ Sending cancel command to the translation process...")
            self.cancel_event.set() 
            self.btn_cancel.configure(state="disabled")

    def start_translation_thread(self):
        input_path = self.entry_input.get()
        output_dir = self.entry_output.get()

        if not input_path or not output_dir:
            messagebox.showwarning("Warning", "Please select input file and output directory.")
            return
        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Input file does not exist.")
            return

        self.cancel_event.clear() 
        self.btn_translate.configure(state="disabled")
        self.btn_cancel.configure(state="normal") 
        self.progress_bar.set(0)
        self.last_progress_percent = -1 
        self.log("Translation started...")
        
        threading.Thread(target=self.run_translation, daemon=True).start()

    def run_translation(self):
        input_path = self.entry_input.get()
        output_dir = self.entry_output.get()
        target_lang = self.combo_lang.get()

        ext = os.path.splitext(input_path)[1].lower()
        lang_code_map = {"English": "en", "Vietnamese": "vi", "Chinese": "zh"}
        target_lang_code = lang_code_map.get(target_lang, "en")

        try:
            self.log(f"Processing file with format: {ext}")

            if ext in ['.xlsx', '.xls']:
                result = handle_excel.process(input_path, output_dir, target_lang_code, self.update_progress, cancel_event=self.cancel_event)
            elif ext in ['.docx', '.doc']:
                result = handle_word.process(input_path, output_dir, target_lang_code, self.update_progress, cancel_event=self.cancel_event, log_callback=self.log)
            elif ext == '.pdf':
                result = handle_pdf.process(input_path, output_dir, target_lang_code, self.update_progress, cancel_event=self.cancel_event, log_callback=self.log)
            else:
                self.log(f"Phát hiện đuôi file lạ '{ext}'...")
                result = handle_raw.process(input_path, output_dir, target_lang_code, self.update_progress, cancel_event=self.cancel_event)

            try:
                tracking.log_translate(input_path, target_lang_code, result)
            except Exception as e:
                logging.warning(f"Tracking translate error: {e}")

            self.log(f"Translation result: {result}")
            self.after(0, lambda: messagebox.showinfo("Thông báo", result))

        except Exception as e:
            error_msg = f"Translation error: {str(e)}"
            self.log(error_msg)
            logging.error("Translation crash:", exc_info=True)
            self.after(0, lambda: messagebox.showerror("System Error", str(e)))

        finally:
            self.after(0, lambda: self.btn_translate.configure(state="normal"))
            self.after(0, lambda: self.btn_cancel.configure(state="disabled"))
            self.log("Translation process finished - UI reset")

if __name__ == "__main__":
    # Check hết hạn đầu tiên, không cần load thêm gì nếu đã hết hạn
    check_expiry_date()
    
    # Nếu qua được hàm check trên, app mới bắt đầu chạy và hiện Loading
    app = TranslatorApp()
    app.mainloop()