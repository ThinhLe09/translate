import os
import sys

print("--- KIỂM TRA MÔI TRƯỜNG ---")
print(f"Python version: {sys.version}")

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    if torch.cuda.is_available():
        print("✅ PyTorch NHÌN THẤY GPU:", torch.cuda.get_device_name(0))
        print("   CUDA Version đang dùng:", torch.version.cuda)
    else:
        print("❌ PyTorch KHÔNG nhìn thấy GPU (Đang xài bản CPU-only).")
except ImportError:
    print("⚠️ Không cài PyTorch (Argostranslate có thể chạy mà không cần PyTorch, nhưng thường đi kèm).")

print("\n--- KIỂM TRA CTRANSLATE2 (Lõi của Argos) ---")
try:
    import ctranslate2
    print(f"CTranslate2 version: {ctranslate2.__version__}")
    
    # Cố tình tạo một dummy translator trên CUDA để ép lỗi lòi ra
    try:
        # Nếu thư viện không build với CUDA, dòng này sẽ văng lỗi ngay
        ctranslate2.Translator("", device="cuda")
    except Exception as e:
        error_msg = str(e)
        if "ValueError: Device cuda is not supported" in error_msg or "compiled without" in error_msg:
             print("❌ CTranslate2 đang được cài đặt KHÔNG HỖ TRỢ CUDA.")
        elif "model path" in error_msg.lower():
             # Nếu nó chửi lỗi đường dẫn model tức là nó ĐÃ CHẤP NHẬN device="cuda"
             print("✅ CTranslate2 HỖ TRỢ CUDA.")
        else:
             print(f"⚠️ Lỗi khởi tạo CUDA: {error_msg}")
except ImportError:
    print("❌ Không tìm thấy thư viện ctranslate2.")

print("\n--- BIẾN MÔI TRƯỜNG ---")
print(f"ARGOS_DEVICE_TYPE = {os.environ.get('ARGOS_DEVICE_TYPE', 'Chưa set!')}")