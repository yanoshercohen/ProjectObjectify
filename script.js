class ProjectObjectify {
    constructor() {
        this.currentScreen = 'upload';
        this.uploadedFile = null;
        this.outputFile = null;
        this.processingInterval = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAnimatedGrid();
        this.setupDragAndDrop();
    }

    setupEventListeners() {
        document.getElementById('file-input').addEventListener('change', this.handleFileSelect.bind(this));
        document.getElementById('browse-btn').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        document.getElementById('upload-area').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        document.getElementById('play-btn').addEventListener('click', this.playVideo.bind(this));
        document.getElementById('download-btn').addEventListener('click', this.downloadVideo.bind(this));
        document.getElementById('new-btn').addEventListener('click', this.resetToUpload.bind(this));
        document.getElementById('restart-btn').addEventListener('click', this.resetToUpload.bind(this));
    }

    setupAnimatedGrid() {
        const canvas = document.getElementById('grid-canvas');
        const ctx = canvas.getContext('2d');

        const resizeCanvas = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        const gridSize = 40;
        const scanLines = [];

        for (let i = 0; i < 3; i++) {
            scanLines.push({
                y: Math.random() * canvas.height,
                speed: 1 + Math.random() * 2
            });
        }

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.strokeStyle = '#333333';
            ctx.lineWidth = 1;

            for (let x = 0; x < canvas.width; x += gridSize) {
                const opacity = Math.max(0.1, 0.5 - Math.abs(x - canvas.width / 2) / canvas.width);
                ctx.globalAlpha = opacity;
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }

            for (let y = 0; y < canvas.height; y += gridSize) {
                const opacity = Math.max(0.1, 0.5 - Math.abs(y - canvas.height / 2) / canvas.height);
                ctx.globalAlpha = opacity;
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }
            ctx.strokeStyle = '#00FFFF';
            ctx.globalAlpha = 0.7;
            ctx.lineWidth = 1;

            scanLines.forEach(line => {
                ctx.beginPath();
                ctx.moveTo(0, line.y);
                ctx.lineTo(canvas.width, line.y);
                ctx.stroke();
                line.y += line.speed;
                if (line.y > canvas.height) {
                    line.y = -10;
                    line.speed = 1 + Math.random() * 2;
                }
            });

            ctx.globalAlpha = 1;
            requestAnimationFrame(animate);
        };

        animate();
    }

    setupDragAndDrop() {
        const uploadArea = document.getElementById('upload-area');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('drag-over');
            }, false);
        });

        uploadArea.addEventListener('drop', this.handleDrop.bind(this), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    handleFile(file) {
        const validTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/x-msvideo', 'video/quicktime'];
        if (!validTypes.includes(file.type)) {
            this.showError('Please select a valid video file (MP4, AVI, MOV)');
            return;
        }

        this.uploadedFile = file;
        this.startProcessing();
    }

    startProcessing() {
        this.showScreen('processing');
        this.updateStatus('PROCESSING');
        document.getElementById('filename').textContent = this.uploadedFile.name;
        const formData = new FormData();
        formData.append('video', this.uploadedFile);
        this.processVideo(formData);
    }

    async processVideo(formData) {
        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Processing failed');
            }
            this.startProgressPolling();

        } catch (error) {
            console.error('Processing error:', error);
            this.showError('Failed to start processing. Please try again.');
        }
    }

    startProgressPolling() {
        this.processingInterval = setInterval(async () => {
            try {
                const response = await fetch('/progress');
                const data = await response.json();

                this.updateProgress(data.progress, data.message);

                if (data.completed) {
                    clearInterval(this.processingInterval);
                    if (data.success) {
                        this.outputFile = data.output_file;
                        this.showComplete();
                    } else {
                        this.showError(data.error || 'Processing failed');
                    }
                }
            } catch (error) {
                console.error('Progress polling error:', error);
            }
        }, 1000);
    }

    updateProgress(progress, message) {
        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        const logText = document.getElementById('log-text');

        progressFill.style.width = `${Math.max(0, Math.min(100, progress))}%`;
        progressPercent.textContent = `${Math.round(progress)}%`;

        if (message) {
            const timestamp = new Date().toLocaleTimeString();
            logText.textContent += `[${timestamp}] ${message}\n`;
            logText.scrollTop = logText.scrollHeight;
        }
    }

    showComplete() {
        this.showScreen('complete');
        this.updateStatus('COMPLETE');

        if (this.outputFile) {
            document.getElementById('output-info').textContent = `Output: ${this.outputFile}`;
        }
    }

    showError(message) {
        this.showScreen('error');
        this.updateStatus('ERROR');
        document.getElementById('error-message').textContent = message;
    }

    showScreen(screenName) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });
        document.getElementById(`${screenName}-screen`).classList.remove('hidden');
        this.currentScreen = screenName;
    }

    updateStatus(status) {
        document.getElementById('status').textContent = status;
    }

    resetToUpload() {
        this.showScreen('upload');
        this.updateStatus('READY');
        this.uploadedFile = null;
        this.outputFile = null;
        document.getElementById('file-input').value = '';
        document.getElementById('progress-fill').style.width = '0%';
        document.getElementById('progress-percent').textContent = '0%';
        document.getElementById('log-text').textContent = '';
        if (this.processingInterval) {
            clearInterval(this.processingInterval);
            this.processingInterval = null;
        }
    }

    async playVideo() {
        if (!this.outputFile) {
            alert('No output file available');
            return;
        }

        try {
            const response = await fetch(`/play/${encodeURIComponent(this.outputFile)}`);
            if (!response.ok) {
                throw new Error('Failed to play video');
            }
            alert('Video opened in default player');
        } catch (error) {
            console.error('Play error:', error);
            alert('Failed to play video');
        }
    }

    async downloadVideo() {
        if (!this.outputFile) {
            alert('No output file available');
            return;
        }

        try {
            const response = await fetch(`/download/${encodeURIComponent(this.outputFile)}`);
            if (!response.ok) {
                throw new Error('Failed to download video');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.outputFile;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download error:', error);
            alert('Failed to download video');
        }
    }
}
document.addEventListener('DOMContentLoaded', () => {
    new ProjectObjectify();
});