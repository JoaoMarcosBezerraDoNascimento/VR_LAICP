import cv2
import zxingcpp
from ultralytics import YOLO
import os
import numpy as np

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
YOLO_PATH = os.path.join(LOCAL_PATH, "YOLOV8s_Barcode_Detection.pt")
model = YOLO(YOLO_PATH)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
PADDING = 20
CROP_HEIGHT = 150
ROTATE_ANGLES = [-10, -5, 0, 5, 10]

def rotate_image(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1)
    return cv2.warpAffine(img, M, (w, h))

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, conf=0.5, verbose=False)

    for box in results[0].boxes.xyxy:
        x1, y1, x2, y2 = map(int, box)

        # Crop com padding
        y1_pad = max(y1 - PADDING, 0)
        y2_pad = min(y2 + PADDING, frame.shape[0])
        x1_pad = max(x1 - PADDING, 0)
        x2_pad = min(x2 + PADDING, frame.shape[1])
        crop = frame[y1_pad:y2_pad, x1_pad:x2_pad]

        # Redimensiona mantendo proporção, esticando levemente horizontal (20%)
        height = CROP_HEIGHT
        width = int(height * crop.shape[1] / crop.shape[0] * 3)
        resized = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)

        # Processamento para ZXing
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # CLAHE para contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(10,10))
        gray = clahe.apply(gray)

        # Threshold global + MORPH_CLOSE para preencher buracos nas barras
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        clean = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Blur leve opcional para suavizar ruído residual
        blur = cv2.GaussianBlur(clean, (1,1), 0)

        # =========================================
        # Visualizar a imagem enviada ao ZXing
        # =========================================
        viz = cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR)
        viz = cv2.resize(viz, (x2 - x1, y2 - y1))
        frame[y1:y2, x1:x2] = viz

        # =========================================
        # Leitura ZXing
        # =========================================
        barcode_found = False
        for angle in ROTATE_ANGLES:
            test_img = rotate_image(blur, angle)
            barcodes = zxingcpp.read_barcodes(test_img)
            if barcodes:
                for b in barcodes:
                    print("Código:", b.text)
            barcode_found = True
            break

        # Retângulo colorido
        color = (0, 255, 0) if barcode_found else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    cv2.imshow("Detector + ZXing Preview", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
