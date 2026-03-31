import openpyxl
import os
import re
from langdetect import detect
import argostranslate.translate
import argostranslate.sbd

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

def process(input_path, output_dir, target_lang_code, progress_callback):
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
        title = sheet.title
        try:
            source_code = smart_detect_lang(title)
            translated_title = do_translation(title, source_code, target_lang_code)
            
            if translated_title != title:
                safe_title = re.sub(r'[\\/*?:\[\]]', '', translated_title)[:31]
                print(f"[DEBUG] Sheet Name: '{title}' [{source_code}] -> '{safe_title}'")
                sheet.title = safe_title
            else:
                print(f"[DEBUG] Skipping Sheet Name: '{title}' (No translation needed)")
        except Exception as e:
            print(f" [ERROR] Translating Sheet Name '{title}': {e}")
            
        current_item += 1
        progress_callback(current_item / total_items)

    print(f"\n[DEBUG] --- STARTING CELL TRANSLATION ---")
    for sheet_title, cell in cells_to_translate:
        original_text = str(cell.value)
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
                print(f" [LỖI] Tại ô {cell.coordinate} (Sheet '{sheet_title}'): {e}")
                translated_lines.append(line)
        
        cell.value = '\n'.join(translated_lines)
        
        preview_orig = original_text.replace('\n', ' ')[:30]
        if is_translated:
            preview_trans = cell.value.replace('\n', ' ')[:30]
            print(f"[DEBUG]  Sheet '{sheet_title}' | Ô {cell.coordinate} | Dịch: '{preview_orig}...' -> '{preview_trans}...'")
        else:
            # Nếu code quyết định không dịch, in ra để xem tại sao (do cùng ngôn ngữ hay detect sai)
            print(f"[DEBUG] Skipping Cell {cell.coordinate} (Sheet '{sheet_title}') | Original: '{preview_orig}...'")

        current_item += 1
        progress_callback(current_item / total_items)

    wb.save(output_file)
    print(f"\n[DEBUG]  FILE SAVED: {output_file}")
    return f"Scanning completed! \nFile saved at: {output_file}"