import cv2
import zxingcpp
import numpy as np
from ultralytics import YOLO
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import os

app = FastAPI()

# =============================
# CONFIGURAÇÕES INICIAIS
# =============================

LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
YOLO_PATH = os.path.join(LOCAL_PATH, "YOLOV8s_Barcode_Detection.pt")
model = YOLO(YOLO_PATH)

PADDING = 20
CROP_HEIGHT = 150
ROTATE_ANGLES = [-10, -5, 0, 5, 10]


# =============================
# FUNÇÃO DE ROTAÇÃO
# =============================
def rotate_image(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1)
    return cv2.warpAffine(img, M, (w, h))


# =============================
# ENDPOINT PRINCIPAL DA API
# =============================
@app.post("/read-barcode/")
async def read_barcode(file: UploadFile = File(...)):

    # 1) Carregar imagem
    img_bytes = await file.read()
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # 2) YOLO detecta o código
    results = model.predict(frame, conf=0.5, verbose=False)

    response_data = []

    if len(results[0].boxes.xyxy) == 0:
        return {"message": "Nenhum código detectado."}

    # 3) Processa cada caixa detectada
    for box in results[0].boxes.xyxy:

        x1, y1, x2, y2 = map(int, box)

        # Crop com padding
        y1_pad = max(y1 - PADDING, 0)
        y2_pad = min(y2 + PADDING, frame.shape[0])
        x1_pad = max(x1 - PADDING, 0)
        x2_pad = min(x2 + PADDING, frame.shape[1])
        crop = frame[y1_pad:y2_pad, x1_pad:x2_pad]

        # Redimensionamento
        height = CROP_HEIGHT
        width = int(height * crop.shape[1] / crop.shape[0] * 3)
        resized = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)

        # Pré-processamento
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(10, 10))
        gray = clahe.apply(gray)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        clean = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        blur = cv2.GaussianBlur(clean, (1, 1), 0)

        # 4) Tenta ler com ZXing (com rotações)
        barcode_text = None

        for angle in ROTATE_ANGLES:
            rotated = rotate_image(blur, angle)
            barcodes = zxingcpp.read_barcodes(rotated)
            if barcodes:
                barcode_text = barcodes[0].text
                break

        # 5) Resposta final
        response_data.append({
            "bbox": {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2)
            },
            "barcode_text": barcode_text
        })

    return JSONResponse(content={"results": response_data})


# =============================
# RODAR LOCALMENTE
# =============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
