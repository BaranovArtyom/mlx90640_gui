from flask import Flask, Response
import socket
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io

app = Flask(__name__)

UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

partial_frame = []

def get_frame():
    global partial_frame

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            floats = list(map(float, data.decode().strip().split(",")))
            partial_frame.extend(floats)

            if len(partial_frame) >= 768:
                frame = np.array(partial_frame[:768], dtype=np.float32).reshape((24, 32))
                partial_frame = partial_frame[768:]

                fig, ax = plt.subplots(figsize=(4, 3))
                ax.axis('off')
                ax.imshow(frame, cmap="inferno")
                canvas = FigureCanvas(fig)
                buf = io.BytesIO()
                canvas.print_png(buf)
                plt.close(fig)
                yield (b'--frame\r\n'
                       b'Content-Type: image/png\r\n\r\n' + buf.getvalue() + b'\r\n')
        except Exception as e:
            print("⚠️ Парсинг:", e)


@app.route('/')
def index():
    return '<h1>MLX90640 Stream</h1><img src="/video">'

@app.route('/video')
def video():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🟢 Server started at http://192.168.1.97:5000/")
    app.run(host='0.0.0.0', port=5000, threaded=True)
