import openpyxl
import os
import re
from langdetect import detect
import argostranslate.translate
import argostranslate.sbd
from concurrent.futures import ThreadPoolExecutor, as_completed # THÊM THƯ VIỆN ĐA LUỒNG

def offline_split_sentences(self, text):
    sentences = re.split(r'(?<=[.!?。！？])\s*', text)
    return [s.strip() for s in sentences if s.strip()]

for name, obj in vars(argostranslate.sbd).items():
    if isinstance(obj, type) and hasattr(obj, 'split_sentences'):
        setattr(obj, 'split_sentences', offline_split_sentences)

def get_translator(from_code, to_code):
    installed_languages = argostranslate.translate.get_installed_languages()
    lang_dict = {lang.code: lang for lang in installed_languages}
    if from_code in lang_dict and to_code in lang_dict:
        return lang_dict[from_code].get_translation(lang_dict[to_code])
    return None

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

# Hàm con được tách ra để chạy đa luồng
def worker_translate_cell(original_text, target_lang_code):
    lines = original_text.splitlines(keepends=False)
    translated_lines = []
    is_translated = False 

    for line in lines:
        if not line.strip():
            translated_lines.append("")
            continue
        try:
            source_code = smart_detect_lang(line)
            trans_line = do_translation(line, source_code, target_lang_code)
            translated_lines.append(trans_line)
            if trans_line != line:
                is_translated = True
        except Exception as e:
            translated_lines.append(line)
            
    return '\n'.join(translated_lines), is_translated

def process(input_path, output_dir, target_lang_code, progress_callback, cancel_event=None):
    print(f"\n{'='*50}")
    print(f"[DEBUG] Start: {os.path.basename(input_path)}")
    print(f"[DEBUG] Target Language: {target_lang_code.upper()}")
    print(f"{'='*50}\n")

    wb = openpyxl.load_workbook(input_path, data_only=True)
    base_name = os.path.basename(input_path)
    file_name, file_ext = os.path.splitext(base_name)
    output_filename = f"{file_name}_Translated_{target_lang_code.upper()}{file_ext}"
    output_file = os.path.join(output_dir, output_filename)

    cells_to_translate = []
    
    for sheet in wb.worksheets:
        print(f"[DEBUG] Scanning Sheet: '{sheet.title}'")
        sheet_valid_cells = 0
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    text = str(cell.value).strip()
                    if text and not text.startswith('='):
                        if re.search(r'[a-zA-Z\u4e00-\u9fffÀ-ỹ]', text):
                            cells_to_translate.append((sheet.title, cell))
                            sheet_valid_cells += 1
        print(f"[DEBUG] -> Found {sheet_valid_cells} valid cells in Sheet '{sheet.title}'.\n")
                        
    total_items = len(cells_to_translate) + len(wb.worksheets)
    current_item = 0
    
    print(f"[DEBUG] --- STARTING SHEET NAME TRANSLATION ---")
    for sheet in wb.worksheets:
        if cancel_event and cancel_event.is_set():
            return "Translation Cancelled by user."

        title = sheet.title
        try:
            source_code = smart_detect_lang(title)
            translated_title = do_translation(title, source_code, target_lang_code)
            
            if translated_title != title:
                safe_title = re.sub(r'[\\/*?:\[\]]', '', translated_title)[:31]
                sheet.title = safe_title
        except Exception as e:
            print(f" [ERROR] Translating Sheet Name '{title}': {e}")
            
        current_item += 1
        progress_callback(current_item / total_items)

    print(f"\n[DEBUG] --- STARTING CELL TRANSLATION (PARALLEL MODE) ---")
    
    print(f"\n[DEBUG] --- STARTING CELL TRANSLATION (PARALLEL MODE) ---")
    
    # -- CODE MỚI: TỰ ĐỘNG TÍNH TOÁN SỐ LUỒNG CHO EXCEL --
    import os
    cpu_cores = os.cpu_count() or 4 # Đo số nhân CPU, nếu lỗi không đo được thì mặc định là 4
    
    # Công thức: Gấp 1.5 lần số nhân CPU (Tối thiểu 4 luồng, Tối đa 32 luồng)
    MAX_WORKERS = max(4, min(32, int(cpu_cores * 1.5))) 
    
    print(f"[DEBUG] System has {cpu_cores} CPU cores. Auto-set MAX_WORKERS = {MAX_WORKERS}")
    # ---------------------------------------------------
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_cell = {}
        for sheet_title, cell in cells_to_translate:
            original_text = str(cell.value)
            future = executor.submit(worker_translate_cell, original_text, target_lang_code)
            future_to_cell[future] = (sheet_title, cell, original_text)

        for future in as_completed(future_to_cell):
            if cancel_event and cancel_event.is_set():
                print("[DEBUG] Nhận lệnh Hủy, đang dừng các luồng...")
                executor.shutdown(wait=False, cancel_futures=True)
                return "Translation Cancelled by user."

            sheet_title, cell, original_text = future_to_cell[future]
            try:
                translated_text, is_translated = future.result()
                cell.value = translated_text
                
                # In debug gọn lại để tránh spam terminal quá nhanh
                if is_translated:
                    pass 
            except Exception as e:
                print(f" [LỖI] Tại ô {cell.coordinate} (Sheet '{sheet_title}'): {e}")

            current_item += 1
            progress_callback(current_item / total_items)

    wb.save(output_file)
    print(f"\n[DEBUG]  FILE SAVED: {output_file}")
    return f"Scanning completed! \nFile saved at: {output_file}"