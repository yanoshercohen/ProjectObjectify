# ProjectObjectify

Object detection and tracking using YOLOv8 and OpenCV.

## Demo


---

## Features

- Object detection with YOLOv8  
- Video processing  
- Object tracking overlays  

---

## Requirements

- Python 3.8+
- OpenCV (`opencv-python`)
- Ultralytics YOLOv8 (`ultralytics`)
- NumPy
- pillow
- MoviePy
- Flask

Install all dependencies:
`pip install flask opencv-python numpy ultralytics moviepy pillow`

---

## Usage

1. Clone the repository:
    ```
    git clone https://github.com/yanoshercohen/ProjectObjectify.git
    cd ProjectObjectify
    ```

3. Run the main script:
    ```
    python server.py
    ```
    - By default - http://127.0.0.1:5000

---

## Notes

- YOLOv8 model weights are downloaded automatically on first run.

---

## Author/s

Yan Osher Cohen & Efraim Holzman

---

## References

- [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
