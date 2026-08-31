"""Quick test: does the OCR endpoint detect text from a synthetic image?"""
import requests, base64, json
from PIL import Image, ImageDraw
import io

# Create a clear test image with large text
img = Image.new('RGB', (800, 400), 'white')
draw = ImageDraw.Draw(img)
draw.text((100, 150), 'Good morning everyone', fill='black')
buf = io.BytesIO()
img.save(buf, format='JPEG', quality=95)
img_b64 = base64.b64encode(buf.getvalue()).decode()

r = requests.post('http://localhost:8000/ocr-translate-base64', json={'image': img_b64, 'direction': 'en->lun'}, timeout=30)
print('Status:', r.status_code)
data = r.json()
print('Regions:', len(data.get('regions', [])))
print('Engine:', data.get('engine'))
if data.get('regions'):
    for reg in data['regions']:
        print(f'  "{reg["original"]}" -> "{reg["translated"]}" (conf={reg["confidence"]})')
else:
    print('No text detected!')
    print('Response:', json.dumps(data, indent=2)[:500])
