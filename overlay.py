import cv2
import numpy as np

# Адрес MJPEG-потока от Flask
thermal_url = 'http://192.168.1.97:5000/video'

# Камера ноутбука
cam = cv2.VideoCapture(0)
thermal_cap = cv2.VideoCapture(thermal_url)

alpha = 0.5  # Прозрачность тепловизора

while True:
    # Получаем кадры
    ret_cam, frame_cam = cam.read()
    ret_thermal, frame_thermal = thermal_cap.read()

    if not ret_cam or not ret_thermal:
        print("Не удалось получить кадры")
        break

    # 🔁 Отразим только вебкамеру по горизонтали (зеркально)
    frame_cam = cv2.flip(frame_cam, 1)

    # Масштабируем тепловизор до размера обычного кадра
    frame_thermal = cv2.resize(frame_thermal, (frame_cam.shape[1], frame_cam.shape[0]))

    # Наложение
    overlaid = cv2.addWeighted(frame_cam, 1 - alpha, frame_thermal, alpha, 0)

    # Отображение
    cv2.imshow("Overlay: Thermal + Webcam", overlaid)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Очистка
cam.release()
thermal_cap.release()
cv2.destroyAllWindows()
