"""
Face detection debug - see what's being detected
"""
import cv2
import time

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

cap = cv2.VideoCapture(0)

print("[Debug] Starting camera. Looking for faces...")
print("[Debug] Try different distances from camera")

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Very relaxed parameters
    faces = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.1,  # More sensitive
        minNeighbors=3,   # Less strict
        minSize=(30, 30)  # Smaller minimum
    )
    
    print(f"\rDetected {len(faces)} face(s)", end="", flush=True)
    
    if len(faces) > 0:
        for (x, y, w, h) in faces:
            print(f"\n  Face at ({x},{y}) size {w}x{h}")
    
    time.sleep(0.5)