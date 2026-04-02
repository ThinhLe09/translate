import os
import re
from langdetect import detect
import argostranslate.translate
import argostranslate.sbd
from functools import lru_cache
def is_binary_file(filepath):

    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return True
    except Exception as e:
        print(f"[DEBUG] Error when reading file: {e}")
        return True #
    return False

def offline_split_sentences(self, text):
    sentences = re.split(r'(?<=[.!?。！？])\s*', text)
    return [s.strip() for s in sentences if s.strip()]

for name, obj in vars(argostranslate.sbd).items():
    if isinstance(obj, type) and hasattr(obj, 'split_sentences'):
        setattr(obj, 'split_sentences', offline_split_sentences)

@lru_cache(maxsize=10)
def get_translator(from_code, to_code):
    installed_languages = argostranslate.translate.get_installed_languages()
    lang_dict = {lang.code: lang for lang in installed_languages}
    if from_code in lang_dict and to_code in lang_dict:
        # argos sẽ tự cache model vào RAM, ta chỉ việc return cái object này
        return lang_dict[from_code].get_translation(lang_dict[to_code])
    return None

def smart_detect_lang(text):
    if not text or not text.strip(): return 'unknown'
    if re.search(r'[\u4e00-\u9fff]', text): return 'zh'
    vi_chars = r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]'
    if re.search(vi_chars, text.lower()): return 'vi'
    try:
        lang = detect(text)
        return 'zh' if lang.startswith('zh') else lang
    except: return 'unknown'

def do_translation(text, source_code, target_lang_code):
    if source_code == target_lang_code or source_code == 'unknown': return text
    translator = get_translator(source_code, target_lang_code)
    if translator: return translator.translate(text)
    elif source_code != 'en' and target_lang_code != 'en':
        trans_to_en = get_translator(source_code, 'en')
        trans_to_target = get_translator('en', target_lang_code)
        if trans_to_en and trans_to_target:
            return trans_to_target.translate(trans_to_en.translate(text))
    return text

def process(input_path, output_dir, target_lang_code, progress_callback):
    print(f"\n[DEBUG] STARTING RAW FILE PROCESSING (TEXT): {os.path.basename(input_path)}")
    
    if is_binary_file(input_path):
        print("[DEBUG]  Detected binary or encoded file. Cancelling processing!")
        return "Translation refused: This file is encoded or in an unsupported format (Binary)!"

    base_name = os.path.basename(input_path)
    file_name, file_ext = os.path.splitext(base_name)
    output_filename = f"{file_name}_Translated_{target_lang_code.upper()}{file_ext}"
    output_file = os.path.join(output_dir, output_filename)

    encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'utf-16']
    content = None
    
    for enc in encodings_to_try:
        try:
            with open(input_path, 'r', encoding=enc) as f:
                content = f.readlines()
            print(f"[DEBUG] Successfully read file with encoding: {enc}")
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        return "System Error: File is binary or in an unsupported text format."

    total_lines = len(content)
    if total_lines == 0: return "File is empty."
    
    translated_content = []
    
    for i, line in enumerate(content):
        original_line = line.rstrip('\n')
        
        if not original_line.strip():
            translated_content.append(original_line)
        else:
            if '<' in original_line and '>' in original_line:
                matches = re.findall(r'>([^<]+)<', original_line)
                trans_line = original_line
                
                for text_chunk in matches:
                    text_chunk_stripped = text_chunk.strip()
                    if text_chunk_stripped and re.search(r'[a-zA-Z\u4e00-\u9fffÀ-ỹ]', text_chunk_stripped):
                        src = smart_detect_lang(text_chunk_stripped)
                        trans_chunk = do_translation(text_chunk_stripped, src, target_lang_code)
                        trans_line = trans_line.replace(f">{text_chunk}<", f">{trans_chunk}<")
                
                translated_content.append(trans_line)
            else:
                if re.search(r'[a-zA-Z\u4e00-\u9fffÀ-ỹ]', original_line):
                    src = smart_detect_lang(original_line)
                    trans_line = do_translation(original_line, src, target_lang_code)
                    translated_content.append(trans_line)
                else:
                    translated_content.append(original_line)
        
        progress_callback((i + 1) / total_lines)

    with open(output_file, 'w', encoding='utf-8') as f:
        for line in translated_content:
            f.write(f"{line}\n")

    return f"Raw text translation completed!\nFile saved at: {output_file}"