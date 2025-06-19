#!/usr/bin/env python3
"""
Instagram-Style ngr.ev-inspired Object Tracking with Original Detection Algorithm
- Modified for web integration
"""

import cv2
import numpy as np
import os
import random
import math
import time
import tempfile
from pathlib import Path

# Try to import YOLO, fallback to basic method if not available
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# Try to import MoviePy for audio preservation
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

class ObjectTracker:
    def __init__(self, use_yolo=True, confidence=0.15, max_distance=50):
        self.use_yolo = use_yolo and YOLO_AVAILABLE
        self.confidence = confidence
        self.max_distance = max_distance
        self.next_id = 0
        self.tracked_objects = {}
        self.disappeared = {}
        self.max_disappeared = 10

        if self.use_yolo:
            print("Loading YOLO model...")
            self.model = YOLO('yolov8m.pt')
        else:
            print("Using background subtraction method...")
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

    def detect_objects_yolo(self, frame):
        """Original YOLO detection algorithm"""
        results = self.model(frame, conf=self.confidence, verbose=False)
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    width = int(x2 - x1)
                    height = int(y2 - y1)
                    detections.append({
                        'center': (center_x, center_y),
                        'bbox': (int(x1), int(y1), width, height),
                        'confidence': conf
                    })
        return detections

    def detect_objects_background(self, frame):
        """Original background subtraction algorithm"""
        fg_mask = self.bg_subtractor.apply(frame)
        kernel = np.ones((5, 5), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                detections.append({
                    'center': (center_x, center_y),
                    'bbox': (x, y, w, h),
                    'confidence': 1.0
                })
        return detections

    def update_tracking(self, detections):
        """Original tracking algorithm"""
        if not detections:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.tracked_objects[obj_id]
                    del self.disappeared[obj_id]
            return self.tracked_objects

        if not self.tracked_objects:
            for detection in detections:
                self.register_object(detection)
            return self.tracked_objects

        used_detection_indices = set()
        for obj_id, obj_data in list(self.tracked_objects.items()):
            min_distance = float('inf')
            best_detection_idx = -1
            for i, detection in enumerate(detections):
                if i in used_detection_indices:
                    continue
                distance = self.calculate_distance(obj_data['center'], detection['center'])
                if distance < min_distance and distance < self.max_distance:
                    min_distance = distance
                    best_detection_idx = i
            if best_detection_idx != -1:
                self.tracked_objects[obj_id] = detections[best_detection_idx]
                self.tracked_objects[obj_id]['id'] = obj_id
                used_detection_indices.add(best_detection_idx)
                if obj_id in self.disappeared:
                    del self.disappeared[obj_id]
            else:
                if obj_id not in self.disappeared:
                    self.disappeared[obj_id] = 1
                else:
                    self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.tracked_objects[obj_id]
                    del self.disappeared[obj_id]
        for i, detection in enumerate(detections):
            if i not in used_detection_indices:
                self.register_object(detection)
        return self.tracked_objects

    def register_object(self, detection):
        """Original object registration"""
        detection['id'] = self.next_id
        self.tracked_objects[self.next_id] = detection
        self.next_id += 1

    def calculate_distance(self, point1, point2):
        """Original distance calculation"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def invert_box_colors(frame, bbox):
    """Invert colors within bounding box"""
    x, y, w, h = bbox
    x = max(0, min(x, frame.shape[1] - w))
    y = max(0, min(y, frame.shape[0] - h))
    if w > 0 and h > 0:
        roi = frame[y:y+h, x:x+w]
        frame[y:y+h, x:x+w] = cv2.bitwise_not(roi)

def draw_effects(frame, tracked_objects, connection_probability=0.3):
    """Enhanced effects with transparent text and color inversion"""
    if not tracked_objects:
        return frame

    height = frame.shape[0]
    font_scale = max(0.4, min(0.8, height / 1000.0))

    objects_to_invert = set()
    connections = []

    # First pass: determine connections
    objects_list = list(tracked_objects.values())
    if len(objects_list) > 1:
        for i in range(len(objects_list)):
            for j in range(i + 1, len(objects_list)):
                if random.random() < connection_probability:
                    obj1 = objects_list[i]
                    obj2 = objects_list[j]

                    pt1 = obj1['center']
                    pt2 = obj2['center']
                    distance = math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)

                    if distance < 200:
                        connections.append((pt1, pt2))

                        if random.random() < 0.5:
                            objects_to_invert.add(obj1['id'])
                            objects_to_invert.add(obj2['id'])

    # Second pass: invert colors for marked objects
    for obj_id in objects_to_invert:
        if obj_id in tracked_objects:
            bbox = tracked_objects[obj_id]['bbox']
            invert_box_colors(frame, bbox)

    # Third pass: draw rectangles and text
    for obj_id, obj_data in tracked_objects.items():
        center = obj_data['center']
        bbox = obj_data['bbox']
        x, y, w, h = bbox

        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 1)

        label = str(obj_id)
        label_x = x + w + 5
        label_y = y + 15

        if label_x < frame.shape[1] - 30 and label_y < frame.shape[0]:
            cv2.putText(frame, label, (label_x, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    # Fourth pass: draw connection lines
    for pt1, pt2 in connections:
        draw_dashed_line(frame, pt1, pt2, (255, 255, 255), 1, 10)

    return frame

def draw_dashed_line(frame, pt1, pt2, color, thickness, dash_length):
    """Original dashed line function"""
    dist = math.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)
    dashes = int(dist / dash_length)
    if dashes == 0:
        return
    for i in range(0, dashes, 2):
        start_ratio = i / dashes
        end_ratio = min((i + 1) / dashes, 1.0)
        start_x = int(pt1[0] + (pt2[0] - pt1[0]) * start_ratio)
        start_y = int(pt1[1] + (pt2[1] - pt1[1]) * start_ratio)
        end_x = int(pt1[0] + (pt2[0] - pt1[0]) * end_ratio)
        end_y = int(pt1[1] + (pt2[1] - pt1[1]) * end_ratio)
        cv2.line(frame, (start_x, start_y), (end_x, end_y), color, thickness)

def merge_audio(input_video, output_video_no_audio, final_output):
    """Original audio merging function"""
    if not MOVIEPY_AVAILABLE:
        print("MoviePy not available. Output video will have no audio.")
        try:
            os.rename(output_video_no_audio, final_output)
        except:
            pass
        return

    try:
        original = VideoFileClip(input_video)
        processed = VideoFileClip(output_video_no_audio)
        if original.audio is not None:
            final_video = processed.set_audio(original.audio)
            final_video.write_videofile(final_output, verbose=False, logger=None)
            final_video.close()
        else:
            processed.close()
            os.rename(output_video_no_audio, final_output)
        original.close()
        processed.close()
        if os.path.exists(output_video_no_audio):
            os.remove(output_video_no_audio)
    except Exception as e:
        print(f"Audio merging failed: {e}")
        print("Saving video without audio...")
        try:
            os.rename(output_video_no_audio, final_output)
        except:
            pass

class VideoProcessor:
    def __init__(self):
        self.progress = 0
        self.message = "Initializing..."
        self.current_frame = 0
        self.total_frames = 0
        self.output_file = None
        self.completed = False
        self.success = False
        self.error = None

    def process_video(self, input_path, output_path=None, use_yolo=True, confidence=0.15, connection_prob=0.3):
        """Modified processing function for web integration"""
        self.completed = False
        self.success = False
        self.error = None
        self.progress = 0
        self.current_frame = 0

        try:
            print(f"=== PROJECT OBJECTIFY ===")
            print(f"Input: {input_path}")

            # Generate output path if not provided
            if output_path is None:
                temp_dir = tempfile.gettempdir()
                output_name = f"objectify_{int(time.time())}.mp4"
                output_path = os.path.join(temp_dir, output_name)

            print(f"Output: {output_path}")
            self.output_file = output_path

            print(f"Method: {'YOLO' if use_yolo and YOLO_AVAILABLE else 'Background Subtraction'}")
            print(f"Confidence: {confidence}")
            print(f"Connection probability: {connection_prob}")

            self.update_progress(5, "Opening video file...")

            # Validate input file
            if not os.path.exists(input_path):
                self.error = f"Input file not found: {input_path}"
                self.completed = True
                return False

            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                self.error = f"Could not open video file: {input_path}"
                self.completed = True
                return False

            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if self.total_frames <= 0:
                self.error = "Invalid video file or no frames detected"
                cap.release()
                self.completed = True
                return False

            self.update_progress(10, f"Video loaded: {width}x{height}, {self.total_frames} frames")

            # Setup output
            temp_output = output_path.replace('.mp4', '_temp.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

            if not out.isOpened():
                self.error = "Could not create output video file"
                cap.release()
                self.completed = True
                return False

            # Initialize tracker
            self.update_progress(15, "Initializing object tracker...")

            tracker = ObjectTracker(use_yolo=use_yolo, confidence=confidence)

            self.update_progress(20, "Processing frames...")

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Detect objects
                    if tracker.use_yolo:
                        detections = tracker.detect_objects_yolo(frame)
                    else:
                        detections = tracker.detect_objects_background(frame)

                    # Update tracking
                    tracked_objects = tracker.update_tracking(detections)

                    # Apply effects
                    frame_with_effects = draw_effects(frame, tracked_objects, connection_prob)

                    # Write frame
                    out.write(frame_with_effects)

                    self.current_frame += 1

                    # Update progress
                    if self.current_frame % 10 == 0 or self.current_frame == self.total_frames:
                        progress = 20 + (self.current_frame / self.total_frames) * 60
                        self.update_progress(progress, f"Processing frame {self.current_frame}/{self.total_frames}")

            except Exception as e:
                self.error = f"Error during frame processing: {str(e)}"
                cap.release()
                out.release()
                self.completed = True
                return False

            cap.release()
            out.release()

            if self.current_frame == 0:
                self.error = "No frames were processed"
                self.completed = True
                return False

            # Merge audio
            self.update_progress(85, "Merging audio...")

            merge_audio(input_path, temp_output, output_path)

            self.update_progress(100, "Processing complete!")

            self.completed = True
            self.success = True
            return True

        except Exception as e:
            self.error = f"Unexpected error: {str(e)}"
            self.completed = True
            return False

    def update_progress(self, progress, message):
        """Update progress and message"""
        self.progress = progress
        self.message = message
        print(f"Progress: {progress:.1f}% - {message}")

    def get_progress(self):
        """Get current progress information"""
        return {
            'progress': self.progress,
            'message': self.message,
            'completed': self.completed,
            'success': self.success,
            'error': self.error,
            'output_file': self.output_file,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames
        }
