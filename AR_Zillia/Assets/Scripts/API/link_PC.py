#pc local/link.py
import os
import time
import socket
import getpass
from typing import Generator, Tuple

import cv2
import numpy as np
import mss
import pyautogui
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import requests

PC_NAME = "JONH_PC"
TARGET_W, TARGET_H = 1920, 1080
TARGET_FPS = 30
JPEG_QUALITY = 60

app = FastAPI(title=PC_NAME)

port = 8555

def registrar_no_servidor() -> None:
    server_base = os.environ.get("SERVER_BASE", "http://100.122.253.126:8555")
    pc_port = int(os.environ.get("PORT", "8555"))

    api_token = os.environ.get("API_TOKEN", "VR_2026")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        my_ip = s.getsockname()[0]
    finally:
        s.close()

    url = f"{server_base}/register"
    body = {"pc_name": PC_NAME, "host": my_ip, "port": pc_port}

    r = requests.post(url, json=body,headers={"x-token": api_token}, timeout=30)
    r.raise_for_status()

def _get_identity() -> Tuple[str, str]:
    host = socket.gethostname()
    user = getpass.getuser()
    return host, user

def _screen_stream_mjpeg() -> Generator[bytes, None, None]:
    host, user = _get_identity()

    frame_interval = 1.0 / max(1.0, float(TARGET_FPS))
    next_deadline = time.perf_counter()
    jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(JPEG_QUALITY)]

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        region = {
            "left": int(monitor["left"]),
            "top": int(monitor["top"]),
            "width": int(monitor["width"]),
            "height": int(monitor["height"]),
        }

        while True:
            now = time.perf_counter()
            if now < next_deadline:
                time.sleep(next_deadline - now)
            else:
                if (now - next_deadline) > 0.25:
                    next_deadline = now
            next_deadline += frame_interval

            img = np.array(sct.grab(region), dtype=np.uint8)
            frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            if frame_bgr.shape[1] != TARGET_W or frame_bgr.shape[0] != TARGET_H:
                frame_bgr = cv2.resize(frame_bgr, (TARGET_W, TARGET_H), interpolation=cv2.INTER_AREA)

            ok, jpg = cv2.imencode(".jpg", frame_bgr, jpeg_params)
            if not ok:
                continue

            payload = jpg.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"X-Host: " + host.encode("utf-8") + b"\r\n"
                b"X-User: " + user.encode("utf-8") + b"\r\n"
                b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n"
                + payload
                + b"\r\n"
            )
            #print("frame_ok", len(payload), flush=True)

@app.get("/info")
def info():
    host, user = _get_identity()
    return {"pc_name": PC_NAME, "host": host, "user": user, "w": TARGET_W, "h": TARGET_H, "target_fps": TARGET_FPS}

@app.get("/stream")
def stream(response: Response):
    host, user = _get_identity()
    response.headers["X-Host"] = host
    response.headers["X-User"] = user
    response.headers["X-Stream"] = "mjpeg"
    response.headers["X-Resolution"] = f"{TARGET_W}x{TARGET_H}"
    response.headers["X-Target-FPS"] = str(TARGET_FPS)

    return StreamingResponse(
        _screen_stream_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

class ClickIn(BaseModel):
    # escolha UM modo:
    # 1) pixels absolutos na tela do PC
    x: float
    y: float

    # se true, interpreta x,y como porcentagem (0..1)
    percent: bool = False

    # botão: "left", "right", "middle"
    button: str = "left"

    # número de cliques
    clicks: int = 1

@app.post("/click")
def click_endpoint(payload: ClickIn):
    # pega tamanho real da tela do PC (não TARGET_W/H do stream)
    sw, sh = pyautogui.size()

    if payload.percent:
        # clamp 0..1
        px = max(0.0, min(1.0, float(payload.x)))
        py = max(0.0, min(1.0, float(payload.y)))
        x = int(px * (sw - 1))
        y = int(py * (sh - 1))
    else:
        # pixels absolutos (clamp)
        x = int(max(0, min(sw - 1, int(payload.x))))
        y = int(max(0, min(sh - 1, int(payload.y))))

    button = payload.button.lower().strip()
    if button not in ("left", "right", "middle"):
        button = "left"

    clicks = int(payload.clicks)
    if clicks < 1:
        clicks = 1
    if clicks > 5:
        clicks = 5

    pyautogui.click(x=x, y=y, clicks=clicks, button=button)
    return {"ok": True, "x": x, "y": y, "screen_w": sw, "screen_h": sh, "button": button, "clicks": clicks}

def print_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    print(f"PC local disponível em: http://{ip}:{port}/stream")

def push_stream_para_servidor() -> None:
    pc_name = os.environ.get("PC_NAME", "JONH_PC")
    server_base = os.environ.get("SERVER_BASE", "http://100.122.253.126:8555")
    api_token = os.environ.get("API_TOKEN", "VR_2026")

    target_w = int(os.environ.get("TARGET_W", "854"))
    target_h = int(os.environ.get("TARGET_H", "480"))
    target_fps = float(os.environ.get("TARGET_FPS", "30"))
    jpeg_quality = int(os.environ.get("JPEG_QUALITY", "40"))

    host = socket.gethostname()
    user = getpass.getuser()

    url = f"{server_base}/ingest/{pc_name}"
    frame_interval = 1.0 / max(1.0, float(target_fps))
    jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        region = {
            "left": int(monitor["left"]),
            "top": int(monitor["top"]),
            "width": int(monitor["width"]),
            "height": int(monitor["height"]),
        }

        sess = requests.Session()
        while True:
            t0 = time.perf_counter()

            img = np.array(sct.grab(region), dtype=np.uint8)
            frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            if frame_bgr.shape[1] != target_w or frame_bgr.shape[0] != target_h:
                frame_bgr = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)

            ok, jpg = cv2.imencode(".jpg", frame_bgr, jpeg_params)
            if ok:
                payload = jpg.tobytes()
                try:
                    sess.post(
                        url,
                        data=payload,
                        headers={
                            "x-token": api_token,
                            "content-type": "image/jpeg",
                            "x-host": host,
                            "x-user": user,
                            "x-w": str(target_w),
                            "x-h": str(target_h),
                        },
                        timeout=5,
                    )
                except Exception:
                    pass

            dt = time.perf_counter() - t0
            sleep_s = frame_interval - dt
            if sleep_s > 0:
                time.sleep(sleep_s)

if __name__ == "__main__":
    registrar_no_servidor()
    push_stream_para_servidor()

