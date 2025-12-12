import cv2
import os

# Try each video device
for i in range(4):
    print(f"Testing /dev/video{i}...")
    cap = cv2.VideoCapture(i)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            filename = f'test_capture_video{i}.jpg'
            cv2.imwrite(filename, frame)
            print(f"✓ Successfully captured from video{i}")
            print(f"  Frame shape: {frame.shape}")
            print(f"  Saved to: {os.path.abspath(filename)}")
        else:
            print(f"✗ video{i} opened but failed to read frame")
        cap.release()
    else:
        print(f"✗ video{i} not available")
    print()

print("Test complete! Check for test_capture_video*.jpg files")