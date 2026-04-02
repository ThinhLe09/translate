import argostranslate.package
import argostranslate.translate
import os
import sys
import argostranslate.sbd  
import re  

argostranslate.settings.device = "cuda"
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def offline_split_sentences(self, text):
    sentences = re.split(r'(?<=[.!?。！？\n])\s*', text)
    return [s.strip() for s in sentences if s.strip()]

for name, obj in vars(argostranslate.sbd).items():
    if isinstance(obj, type) and hasattr(obj, 'split_sentences'):
        setattr(obj, 'split_sentences', offline_split_sentences)


def _get_model_dir():
    """Auto-detect the 'model' folder next to main.py or the .exe"""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller executable
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as a script – go up one level from plugin/ to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'model')


def load_models():
    """Scan the model folder and install every .argosmodel file found."""
    model_dir = _get_model_dir()
    print(f" Loading models from: {model_dir}")

    if not os.path.isdir(model_dir):
        print(f" Model directory not found at: {model_dir}")
        return

    loaded = 0
    for filename in sorted(os.listdir(model_dir)):
        if filename.endswith('.argosmodel'):
            path = os.path.join(model_dir, filename)
            try:
                argostranslate.package.install_from_path(path)
                print(f" Successfully loaded: {filename}")
                loaded += 1
            except Exception as e:
                print(f" Error loading {filename}: {e}")

    if loaded == 0:
        print(" Warning: No .argosmodel files found in the model directory!")
    else:
        print(f" Total models loaded: {loaded}")

    print("\n" + "="*40 + "\n")


# --- Auto-load models on first import ---
load_models()


# ---- Test utilities (only run when executed directly) ----
if __name__ == "__main__":
    installed_languages = argostranslate.translate.get_installed_languages()
    lang_dict = {lang.code: lang for lang in installed_languages}

    def run_test(text, from_code, to_code):
        if from_code in lang_dict and to_code in lang_dict:
            source_lang = lang_dict[from_code]
            target_lang = lang_dict[to_code]
            translator = source_lang.get_translation(target_lang)
            if translator:
                result = translator.translate(text)
                print(f"[{from_code.upper()} -> {to_code.upper()}]")
                print(f" Original : {text}")
                print(f" Translated: {result}\n")
            else:
                print(f" No direct translation path from {from_code} to {to_code}\n")
        else:
            print(f"Language {from_code} or {to_code} is not installed!\n")

    print(" STARTING TRANSLATION TEST:\n")
    run_test("Tôi đang tập trung hoàn thiện đồ án tốt nghiệp về hệ thống hỏi đáp trực quan.", "vi", "en")
    run_test("We need to parse the XML files to extract the schema logic accurately.", "en", "vi")
    run_test("The model architecture utilizes attention masking to improve accuracy.", "en", "zh")
    run_test("人工智能和多模态模型是未来的发展趋势。", "zh", "en")