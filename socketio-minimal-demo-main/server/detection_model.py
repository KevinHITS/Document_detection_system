import cv2
import numpy as np
from PIL import Image
import fitz
import io
import logging

logger = logging.getLogger(__name__)

def detect_vertical_simple_pil(pil_image):
    try:
        img_array = np.array(pil_image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            aspect_ratio = w / h if h > 0 else 0
            is_vertical = aspect_ratio < 1
            logger.info(f"Width: {w}, Height: {h}")
            logger.info(f"Aspect ratio: {aspect_ratio:.2f}")
            logger.info(f"Text is: {'Vertical' if is_vertical else 'Horizontal'}")
            return is_vertical, aspect_ratio, w, h
        logger.warning("No contours found in image")
        return False, 0, 0, 0
    except Exception as e:
        logger.error(f"Error in detect_vertical_simple_pil: {e}")
        return False, 0, 0, 0

def get_pdf_page_count(file_path):
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        logger.info(f"PDF has {page_count} pages: {file_path}")
        return page_count
    except Exception as e:
        logger.error(f"Error getting page count from PDF {file_path}: {e}")
        return 0

def extract_pages_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        pages = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            pages.append(pil_image)
        doc.close()
        logger.info(f"Successfully extracted {len(pages)} pages from PDF: {file_path}")
        return pages
    except Exception as e:
        logger.error(f"Error extracting pages from PDF {file_path}: {e}")
        return []

def analyze_document(file_path):
    try:
        results = {'file_type': 'unknown', 'total_pages': 0, 'results': []}
        if file_path.lower().endswith('.pdf'):
            results['file_type'] = 'pdf'
            pages = extract_pages_from_pdf(file_path)
            results['total_pages'] = len(pages)
            for page_num, pil_image in enumerate(pages, 1):
                is_vertical, aspect_ratio, width, height = detect_vertical_simple_pil(pil_image)
                page_result = {
                    'page': page_num,
                    'is_vertical': is_vertical,
                    'aspect_ratio': round(aspect_ratio, 2),
                    'width': width,
                    'height': height,
                    'orientation': 'Vertical' if is_vertical else 'Horizontal'
                }
                results['results'].append(page_result)
        else:
            results['file_type'] = 'image'
            results['total_pages'] = 1
            pil_image = Image.open(file_path)
            is_vertical, aspect_ratio, width, height = detect_vertical_simple_pil(pil_image)
            page_result = {
                'page': 1,
                'is_vertical': is_vertical,
                'aspect_ratio': round(aspect_ratio, 2),
                'width': width,
                'height': height,
                'orientation': 'Vertical' if is_vertical else 'Horizontal'
            }
            results['results'].append(page_result)
        return results
    except Exception as e:
        logger.error(f"Error analyzing document {file_path}: {e}")
        return {'file_type': 'error', 'total_pages': 0, 'results': [], 'error': str(e)}

def detect_vertical_advanced(pil_image):
    return detect_vertical_simple_pil(pil_image)

def detect_vertical_ml_based(pil_image):
    return detect_vertical_simple_pil(pil_image)