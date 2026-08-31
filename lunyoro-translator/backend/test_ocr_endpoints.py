"""Quick test for OCR translate endpoints."""
import requests, base64, io
from PIL import Image, ImageDraw

# Create a test image with text
img = Image.new('RGB', (400, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((50, 50), 'Good morning', fill='black')
draw.text((50, 100), 'How are you today', fill='black')
draw.text((50, 150), 'The market is open', fill='black')

buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

# Test 1: Upload endpoint
print('=== TEST: /ocr-translate (file upload) ===')
files = {'file': ('test.jpg', buf.getvalue(), 'image/jpeg')}
r = requests.post('http://localhost:8000/ocr-translate?direction=en->lun', files=files, timeout=120)
d = r.json()
print(f'Status: {r.status_code}')
if 'error' in d:
    print(f'Error: {d["error"]}')
else:
    print(f'Detected: {d.get("total_detected", 0)}, Translated: {d.get("total_translated", 0)}')
    for region in d.get('regions', [])[:5]:
        print(f'  "{region["original"]}" -> "{region["translated"]}" ({region["confidence"]})')
print()

# Test 2: Base64 endpoint
print('=== TEST: /ocr-translate-base64 (camera frame) ===')
buf.seek(0)
b64 = base64.b64encode(buf.getvalue()).decode()
r = requests.post('http://localhost:8000/ocr-translate-base64',
    json={'image': f'data:image/jpeg;base64,{b64}', 'direction': 'en->lun'}, timeout=120)
d = r.json()
print(f'Status: {r.status_code}')
if 'error' in d:
    print(f'Error: {d["error"]}')
else:
    print(f'Regions: {len(d.get("regions", []))}')
    for region in d.get('regions', [])[:5]:
        print(f'  "{region["original"]}" -> "{region["translated"]}" ({region["confidence"]})')

print('\n=== BOTH TESTS COMPLETE ===')
