import openpyxl
import os
import re
from langdetect import detect
import argostranslate.translate
import argostranslate.sbd
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

def offline_split_sentences(self, text):
    sentences = re.split(r'(?<=[.!?。！？])\s*', text)
    return [s.strip() for s in sentences if s.strip()]

for name, obj in vars(argostranslate.sbd).items():
    if isinstance(obj, type) and hasattr(obj, 'split_sentences'):
        setattr(obj, 'split_sentences', offline_split_sentences)

@lru_cache(maxsize=50000)
def get_translator(from_code, to_code):
    installed_languages = argostranslate.translate.get_installed_languages()
    lang_dict = {lang.code: lang for lang in installed_languages}
    if from_code in lang_dict and to_code in lang_dict:
        return lang_dict[from_code].get_translation(lang_dict[to_code])
    return None
@lru_cache(maxsize=50000)
def smart_detect_lang(text):
    if not text or not text.strip():
        return 'unknown'
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    vi_chars = r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]'
    if re.search(vi_chars, text.lower()):
        return 'vi'
    try:
        lang = detect(text)
        return 'zh' if lang.startswith('zh') else lang
    except:
        return 'unknown'

def do_translation(text, source_code, target_lang_code):
    if source_code == target_lang_code or source_code == 'unknown':
        return text
    translator = get_translator(source_code, target_lang_code)
    if translator:
        return translator.translate(text)
    elif source_code != 'en' and target_lang_code != 'en':
        trans_to_en = get_translator(source_code, 'en')
        trans_to_target = get_translator('en', target_lang_code)
        if trans_to_en and trans_to_target:
            en_text = trans_to_en.translate(text)
            return trans_to_target.translate(en_text)
    return text

def worker_translate_cell(original_text, target_lang_code):
    # Kiểm tra ô rỗng
    if not original_text or not str(original_text).strip():
        return original_text, False

    try:
        # 1. Nhận diện ngôn ngữ 1 LẦN cho toàn bộ nội dung ô
        source_code = smart_detect_lang(original_text)
        
        # 2. QUĂNG NGUYÊN CỤC TEXT VÀO MODEL (GPU sẽ tự động batching bên trong)
        trans_text = do_translation(original_text, source_code, target_lang_code)
        
        is_translated = (trans_text != original_text)
        return trans_text, is_translated
        
    except Exception as e:
        # Nếu lỗi (rất hiếm), trả về text gốc để không làm hỏng file
        return original_text, False
    
def process(input_path, output_dir, target_lang_code, progress_callback, cancel_event=None, log_callback=None):
    # Hàm hỗ trợ in log ra Terminal hoặc UI
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log(f"\n{'='*50}")
    log(f"[INFO] Initializing Excel Translation Engine...")
    log(f"[INFO] Target File: {os.path.basename(input_path)}")
    log(f"[INFO] Target Language: {target_lang_code.upper()}")
    log(f"{'='*50}\n")

    log("[INFO] Loading Excel workbook into memory. Please wait...")
    wb = openpyxl.load_workbook(input_path, data_only=True)
    base_name = os.path.basename(input_path)
    file_name, file_ext = os.path.splitext(base_name)
    output_filename = f"{file_name}_Translated_{target_lang_code.upper()}{file_ext}"
    output_file = os.path.join(output_dir, output_filename)

    cells_to_translate = []
    
    log("[INFO] Scanning worksheets for translatable content...")
    for sheet in wb.worksheets:
        sheet_valid_cells = 0
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    text = str(cell.value).strip()
                    if text and not text.startswith('='):
                        if re.search(r'[a-zA-Z\u4e00-\u9fffÀ-ỹ]', text):
                            cells_to_translate.append((sheet.title, cell))
                            sheet_valid_cells += 1
        log(f"[DEBUG] -> Sheet '{sheet.title}': Found {sheet_valid_cells} valid cells.")
                        
    total_items = len(cells_to_translate) + len(wb.worksheets)
    current_item = 0
    
    log("\n[INFO] Phase 1: Translating worksheet names...")
    for sheet in wb.worksheets:
        if cancel_event and cancel_event.is_set():
            log("[WARNING] Translation cancelled by user during Phase 1.")
            return "Translation Cancelled by user."

        title = sheet.title
        try:
            source_code = smart_detect_lang(title)
            translated_title = do_translation(title, source_code, target_lang_code)
            
            if translated_title != title:
                safe_title = re.sub(r'[\\/*?:\[\]]', '', translated_title)[:31]
                sheet.title = safe_title
        except Exception as e:
            log(f"[ERROR] Failed to translate sheet name '{title}': {e}")
            
        current_item += 1
        progress_callback(current_item / total_items)

    log("\n[INFO] Phase 2: Translating cell contents (GPU Optimized Mode)...")
    
    # -- TỐI ƯU HÓA GPU TẠI ĐÂY --
    # GPU cần ít luồng hơn CPU để tránh tràn VRAM. 2 đến 4 luồng là mức an toàn và nhanh nhất.
    cpu_cores = os.cpu_count() or 4
    MAX_WORKERS = min(4, cpu_cores) 
    
    log(f"[INFO] Hardware configuration applied: Using {MAX_WORKERS} concurrent threads to prevent GPU memory overflow.")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_cell = {}
        for sheet_title, cell in cells_to_translate:
            original_text = str(cell.value)
            future = executor.submit(worker_translate_cell, original_text, target_lang_code)
            future_to_cell[future] = (sheet_title, cell, original_text)

        # Biến đếm để in log gọn gàng hơn
        translated_count = 0
        total_cells = len(cells_to_translate)

        for future in as_completed(future_to_cell):
            if cancel_event and cancel_event.is_set():
                log("[WARNING] Translation abort signal received. Shutting down worker threads...")
                executor.shutdown(wait=False, cancel_futures=True)
                return "Translation Cancelled by user."

            sheet_title, cell, original_text = future_to_cell[future]
            try:
                translated_text, is_translated = future.result()
                cell.value = translated_text
            except Exception as e:
                log(f"[ERROR] Cell {cell.coordinate} in Sheet '{sheet_title}': {e}")

            current_item += 1
            translated_count += 1
            progress_callback(current_item / total_items)

            # In log tiến độ mỗi 50 ô (tránh làm tràn UI/Terminal)
            if translated_count % 50 == 0 or translated_count == total_cells:
                percent = (translated_count / total_cells) * 100
                log(f"[PROGRESS] Translated {translated_count}/{total_cells} cells ({percent:.1f}%) - Processing on GPU...")

    log(f"\n[INFO] Saving translated workbook... Do not close the application.")
    wb.save(output_file)
    log(f"[SUCCESS] File saved successfully at:\n{output_file}")
    
    return f"Translation completed successfully!\nFile saved at: {os.path.basename(output_file)}"