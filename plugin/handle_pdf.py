import os
import tempfile
import uuid
from pdf2docx import Converter
from plugin import handle_word  

def process(input_path, output_dir, target_lang_code, progress_callback, cancel_event=None, log_callback=None):
    # Function: Nếu có log_callback của App thì xài, không thì in ra CMD
    def log(msg):
        if log_callback: log_callback(msg)
        else: print(msg)

    log(f"STARTING PDF PROCESSING: {os.path.basename(input_path)}")
    
    base_name = os.path.basename(input_path)
    file_name, _ = os.path.splitext(base_name)
    
    temp_dir = tempfile.gettempdir()
    temp_docx_path = os.path.join(temp_dir, f"bosch_pdf_temp_{uuid.uuid4().hex}.docx")
    
    log("Extracting PDF to Word format (Flow-layout)...")
    log("⏳ This stage may take 30s - 2 minutes depending on file size. Please be patient...")
    try:
        cv = Converter(input_path)
        progress_callback(0.1)
        cv.convert(temp_docx_path, start=0, end=None)
        cv.close()
    except Exception as e:
        return f"Error extracting PDF to Word: {e}"

    if not os.path.exists(temp_docx_path):
        return "System Error: Unable to create temporary Word file."

    if cancel_event and cancel_event.is_set():
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
        return "PDF processing has been CANCELLED!"

    log("Translating and preserving formatting...")
    output_filename = f"{file_name}_Translated_{target_lang_code.upper()}.docx"
    output_file = os.path.join(output_dir, output_filename)
    
    try:
        # Pass log_callback to handle_word
        result = handle_word.process_core(temp_docx_path, output_file, target_lang_code, progress_callback, cancel_event, log_callback)
    except Exception as e:
        result = f"Error during translation from virtual file: {e}"
    
    try:
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
    except Exception:
        pass
        
    return result