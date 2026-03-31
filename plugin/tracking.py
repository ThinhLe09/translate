

import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TRACKING_DIR = os.path.join(BASE_DIR, 'tracking')
os.makedirs(TRACKING_DIR, exist_ok=True)
TRACKING_FILE = os.path.join(TRACKING_DIR, 'user_tracking.csv')
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TRACKING_DIR = os.path.join(BASE_DIR, 'tracking')
os.makedirs(TRACKING_DIR, exist_ok=True)
def log_event(event_type, purpose=None, file_name=None, file_type=None, target_lang=None, extra=None):
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user = os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown'
    row = [now, user, event_type, purpose or '', file_name or '', file_type or '', target_lang or '', extra or '']
    write_header = not os.path.exists(TRACKING_FILE)
    with open(TRACKING_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['timestamp', 'user', 'event_type', 'purpose', 'file_name', 'file_type', 'target_lang', 'extra'])
        writer.writerow(row)

def log_app_open(purpose=None):
    log_event('open', purpose)

def log_app_close():
    log_event('close')

def log_translate(file_path, target_lang, result=None):
    file_name = os.path.basename(file_path)
    file_type = os.path.splitext(file_path)[1].lower().replace('.', '')
    log_event('translate', purpose='translate_file', file_name=file_name, file_type=file_type, target_lang=target_lang, extra=result)