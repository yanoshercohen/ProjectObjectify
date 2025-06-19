from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import tempfile
import threading
import time
import subprocess
import sys
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid

# Import our video processing model
from object_detection_model import VideoProcessor

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Global variables for processing state
current_processor = None
processing_lock = threading.Lock()

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/style.css')
def styles():
    """Serve the CSS file"""
    return send_from_directory('.', 'style.css')

@app.route('/script.js')
def scripts():
    """Serve the JavaScript file"""
    return send_from_directory('.', 'script.js')

@app.route('/process', methods=['POST'])
def process_video():
    """Handle video upload and start processing"""
    global current_processor

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload MP4, AVI, MOV, MKV, WMV, or FLV files'}), 400

    with processing_lock:
        if current_processor and not current_processor.completed:
            return jsonify({'error': 'Another video is currently being processed'}), 409

        try:
            temp_dir = tempfile.mkdtemp()

            filename = secure_filename(file.filename)
            input_path = os.path.join(temp_dir, filename)
            file.save(input_path)

            output_filename = f"objectify_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(temp_dir, output_filename)

            current_processor = VideoProcessor()

            processing_thread = threading.Thread(
                target=current_processor.process_video,
                args=(input_path, output_path),
                kwargs={'use_yolo': True, 'confidence': 0.15, 'connection_prob': 0.3},
                daemon=True
            )
            processing_thread.start()

            return jsonify({'success': True, 'message': 'Processing started'})

        except Exception as e:
            return jsonify({'error': f'Failed to start processing: {str(e)}'}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Get current processing progress"""
    global current_processor

    if not current_processor:
        return jsonify({
            'progress': 0,
            'message': 'No processing in progress',
            'completed': False,
            'success': False
        })

    progress_info = current_processor.get_progress()
    return jsonify(progress_info)

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed video file"""
    global current_processor

    if not current_processor or not current_processor.output_file:
        return jsonify({'error': 'No output file available'}), 404

    try:
        if os.path.exists(current_processor.output_file):
            return send_file(
                current_processor.output_file,
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({'error': 'Output file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/play/<filename>')
def play_file(filename):
    """Open the processed video file in default player"""
    global current_processor

    if not current_processor or not current_processor.output_file:
        return jsonify({'error': 'No output file available'}), 404

    try:
        if os.path.exists(current_processor.output_file):
            if os.name == 'nt':  # Windows
                os.startfile(current_processor.output_file)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', current_processor.output_file])

            return jsonify({'success': True, 'message': 'Video opened in default player'})
        else:
            return jsonify({'error': 'Output file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to open video: {str(e)}'}), 500

@app.route('/status')
def status():
    return jsonify({
        'status': 'running',
        'version': '1.0.0',
        'yolo_available': hasattr(current_processor, 'use_yolo') if current_processor else False
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []

    try:
        import cv2
    except ImportError:
        missing_deps.append('opencv-python')

    try:
        import numpy
    except ImportError:
        missing_deps.append('numpy')

    try:
        from PIL import Image
    except ImportError:
        missing_deps.append('Pillow')

    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall with: pip install " + " ".join(missing_deps))
        return False

    return True

def print_banner():
    print("""
    ╔══════════════════════════════════════╗
    ║        PROJECT OBJECTIFY             ║
    ║        Web Interface Server          ║
    ║                                      ║
    ║  Object Tracking                     ║
    ║  with Modern Web Interface           ║
    ╚══════════════════════════════════════╝
    """)

def main():
    """Main function to run the server"""
    print_banner()

    if not check_dependencies():
        print("\nPlease install missing dependencies before running the server.")
        return 1

    required_files = ['index.html', 'style.css', 'script.js']
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print(f"Missing required files: {', '.join(missing_files)}")
        print("Please ensure all web files are in the same directory as this server.")
        return 1

    print("\nStarting server...")
    print("Dependencies: ✓")
    print("Web files: ✓")

    # Additional dependency checks
    try:
        from ultralytics import YOLO
        print("YOLO: ✓ (Advanced object detection available)")
    except ImportError:
        print("YOLO: ✗ (Will use background subtraction)")
        print("  Install with: pip install ultralytics")

    try:
        from moviepy.editor import VideoFileClip
        print("MoviePy: ✓ (Audio preservation available)")
    except ImportError:
        print("MoviePy: ✗ (Videos will be processed without audio)")
        print("  Install with: pip install moviepy")

    print("\n" + "=" * 50)
    print("🚀 Server starting on http://localhost:5000")
    print("📁 Upload videos and apply Instagram-style effects")
    print("⚡ Real-time processing with progress tracking")
    print("🎬 Automatic audio preservation (if MoviePy available)")
    print("=" * 50)

    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        return 0
    except Exception as e:
        print(f"\nServer error: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
    