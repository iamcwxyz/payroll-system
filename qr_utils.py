import qrcode
import os
from PIL import Image
import io

def generate_employee_qr_code(employee_id, name, employee_db_id):
    """
    Generate QR code for employee containing their Employee ID
    Returns the file path of the generated QR code
    """
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join('static', 'uploads', 'qr_codes')
    os.makedirs(upload_dir, exist_ok=True)
    
    # QR code data - using employee_id as the primary identifier for scanning
    qr_data = employee_id
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,  # Size of QR code (1 is smallest)
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Error correction level
        box_size=10,  # Size of each box in pixels
        border=4,  # Border size in boxes
    )
    
    # Add data to QR code
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Create a larger image with employee info
    img_width, img_height = qr_img.size
    final_height = img_height + 80  # Add space for text
    final_img = Image.new('RGB', (img_width, final_height), 'white')
    
    # Paste QR code
    final_img.paste(qr_img, (0, 0))
    
    # Save the QR code
    filename = f"qr_{employee_id}_{employee_db_id}.png"
    file_path = os.path.join(upload_dir, filename)
    final_img.save(file_path)
    
    # Return relative path for database storage
    return os.path.join('qr_codes', filename)

def get_employee_qr_download_path(qr_code_path):
    """
    Get the full file system path for QR code download
    """
    if not qr_code_path:
        return None
    
    return os.path.join('static', 'uploads', qr_code_path)

def verify_qr_scan_data(scanned_data):
    """
    Verify if scanned data matches expected employee ID format
    Returns (is_valid, cleaned_employee_id)
    """
    if not scanned_data:
        return False, None
    
    # Clean the scanned data
    cleaned_data = scanned_data.strip().upper()
    
    # Check if it matches employee ID pattern (EMP001, EMP002, etc.)
    import re
    if re.match(r'^EMP\d{3,}$', cleaned_data):
        return True, cleaned_data
    
    # Also allow direct numeric input (for flexibility)
    if cleaned_data.isdigit():
        return True, f"EMP{cleaned_data.zfill(3)}"
    
    return False, None