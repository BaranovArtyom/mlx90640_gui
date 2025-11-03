import cv2
import numpy as np
import socket
import time
from flask import Flask, Response, jsonify, render_template

app = Flask(__name__, static_folder='static', template_folder='templates')

# ==== Настройки UDP ====
UDP_IP = "0.0.0.0"
UDP_PORT = 12345
sock = socket.socket(socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# ==== Глобальные переменные ====
partial_frame = []
latest_thermal_array = np.zeros((24, 32), dtype=np.float32)
latest_tmin = 0.0
latest_tmax = 0.0

# ==== Камера ====
cam = cv2.VideoCapture(0)
alpha = 0.5  # прозрачность наложения

# ==== Получение кадров от ESP ====
def thermal_receiver():
    global partial_frame, latest_thermal_array, latest_tmin, latest_tmax

    # ⚠️ создаём сокет ВНУТРИ потока
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            decoded = data.decode().strip()
            if decoded.startswith("S|"):
                partial_frame = []
                decoded = decoded[2:]

            floats = list(map(float, decoded.split(",")))
            partial_frame.extend(floats)

            if len(partial_frame) >= 768:
                frame = np.array(partial_frame[:768], dtype=np.float32).reshape((24, 32))
                partial_frame = partial_frame[768:]
                latest_thermal_array = frame
                latest_tmin = float(frame.min())
                latest_tmax = float(frame.max())
        except Exception as e:
            print("⚠️ Ошибка парсинга:", e)


# ==== Генератор тепловизионного потока ====
def get_thermal_stream():
    while True:
        # Нормализуем для отображения
        norm = cv2.normalize(latest_thermal_array, None, 0, 255, cv2.NORM_MINMAX)
        thermal_colormap = cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_INFERNO)
        thermal_colormap = cv2.resize(thermal_colormap, (640, 480), interpolation=cv2.INTER_NEAREST)

        # Добавим надпись
        label = f"Tmin = {latest_tmin:.1f} C, Tmax = {latest_tmax:.1f} C"
        cv2.putText(thermal_colormap, label, (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2, cv2.LINE_AA)

        ret, jpeg = cv2.imencode('.jpg', thermal_colormap)
        if not ret:
            continue

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.04)  # ~25 FPS

# ==== Генератор overlay потока ====
def get_overlay_stream():
    while True:
        ret_cam, frame_cam = cam.read()
        if not ret_cam:
            print("❌ Нет кадра с камеры")
            continue

        frame_cam = cv2.flip(frame_cam, 1)
        frame_cam = cv2.resize(frame_cam, (640, 480))

        norm = cv2.normalize(latest_thermal_array, None, 0, 255, cv2.NORM_MINMAX)
        thermal_colormap = cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_INFERNO)
        thermal_colormap = cv2.resize(thermal_colormap, (640, 480), interpolation=cv2.INTER_NEAREST)

        overlaid = cv2.addWeighted(frame_cam, 1 - alpha, thermal_colormap, alpha, 0)

        label = f"Tmin = {latest_tmin:.1f} C, Tmax = {latest_tmax:.1f} C"
        cv2.putText(overlaid, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)

        ret, jpeg = cv2.imencode('.jpg', overlaid)
        if not ret:
            continue

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.04)

# ==== Flask маршруты ====
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/video')
def video():
    return Response(get_thermal_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/overlay')
def overlay():
    return Response(get_overlay_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify({"tmin": latest_tmin, "tmax": latest_tmax})

# ==== Запуск ====
if __name__ == '__main__':
    import threading
    threading.Thread(target=thermal_receiver, daemon=True).start()
    print("🟢 Flask server started at: http://192.168.1.97:5000/")
    app.run(host='0.0.0.0', port=5000, threaded=True)
