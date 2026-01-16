"""
Video Translator - Auto recognize English speech and add Chinese subtitles
Using faster-whisper + PyQt6 (supports Python 3.13)
"""
import sys
import os
import subprocess
import tempfile
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QProgressBar,
    QComboBox, QGroupBox, QMessageBox, QFileDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont

from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator


class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)


class VideoTranslator:
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    def __init__(self, signals: WorkerSignals):
        self.signals = signals
        self.model = None
        
    def log(self, message: str):
        self.signals.log.emit(message)
        
    def load_model(self, model_size: str = "base"):
        self.log(f"Loading Whisper model ({model_size})...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.log("Model loaded")
        
    def extract_audio(self, video_path: str, audio_path: str) -> bool:
        self.log(f"Extracting audio: {os.path.basename(video_path)}")
        try:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                '-y', audio_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode != 0:
                self.log(f"FFmpeg error: {result.stderr}")
                return False
            return True
        except FileNotFoundError:
            self.log("Error: FFmpeg not found. Please install FFmpeg and add to PATH")
            return False
        except Exception as e:
            self.log(f"Extract audio failed: {str(e)}")
            return False
    
    def transcribe_audio(self, audio_path: str) -> list:
        self.log("Transcribing audio...")
        segments_result, info = self.model.transcribe(
            audio_path,
            language="en",
            task="transcribe",
        )
        segments = []
        for seg in segments_result:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })
        self.log(f"Transcription done, {len(segments)} segments")
        return segments
    
    def translate_text(self, text: str) -> str:
        if not text.strip():
            return ""
        try:
            translator = GoogleTranslator(source='en', target='zh-CN')
            return translator.translate(text)
        except Exception as e:
            self.log(f"Translation failed: {str(e)}")
            return text
    
    def translate_segments(self, segments: list) -> list:
        self.log("Translating subtitles...")
        total = len(segments)
        for i, seg in enumerate(segments):
            seg["translated"] = self.translate_text(seg["text"])
            if (i + 1) % 10 == 0:
                self.log(f"Translation progress: {i + 1}/{total}")
        self.log("Translation done")
        return segments
    
    def format_time_srt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def save_srt(self, segments: list, srt_path: str):
        self.log("Saving subtitle file...")
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start = self.format_time_srt(seg["start"])
                end = self.format_time_srt(seg["end"])
                text = seg.get("translated", seg["text"])
                original = seg["text"]
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n")
                f.write(f"{original}\n")
                f.write("\n")
        self.log(f"Subtitle saved: {os.path.basename(srt_path)}")
    
    def embed_subtitle(self, video_path: str, srt_path: str, output_path: str) -> bool:
        self.log("Embedding subtitle to video...")
        try:
            srt_path_escaped = srt_path.replace('\\', '/').replace(':', r'\:')
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f"subtitles='{srt_path_escaped}':force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
                '-c:a', 'copy',
                '-y', output_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode != 0:
                self.log(f"Embed subtitle failed: {result.stderr}")
                return False
            self.log(f"Output video: {os.path.basename(output_path)}")
            return True
        except Exception as e:
            self.log(f"Embed subtitle error: {str(e)}")
            return False
    
    def process_video(self, video_path: str, output_dir: str = None) -> bool:
        video_path = Path(video_path)
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = video_path.parent
        
        output_name = f"{video_path.stem}_subtitle{video_path.suffix}"
        output_path = output_dir / output_name
        srt_name = f"{video_path.stem}_subtitle.srt"
        srt_path = output_dir / srt_name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "audio.wav")
            
            if not self.extract_audio(str(video_path), audio_path):
                return False
            
            segments = self.transcribe_audio(audio_path)
            if not segments:
                self.log("No speech detected")
                return False
            
            segments = self.translate_segments(segments)
            self.save_srt(segments, str(srt_path))
            
            if not self.embed_subtitle(str(video_path), str(srt_path), str(output_path)):
                return False
        
        return True


class DropArea(QListWidget):
    files_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 14px;
            }
            QListWidget:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QListWidget {
                    border: 2px dashed #4CAF50;
                    border-radius: 10px;
                    background-color: #c8e6c9;
                    font-size: 14px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 14px;
            }
            QListWidget:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 14px;
            }
            QListWidget:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
        """)
        
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        files.append(filepath)
        
        self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_files = []
        self.is_processing = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Video Translator - English to Chinese Subtitle")
        self.setMinimumSize(700, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Video Translator")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Auto recognize English speech and generate bilingual subtitles")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(subtitle)
        
        drop_group = QGroupBox("Drag video files or folders here")
        drop_layout = QVBoxLayout(drop_group)
        
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.on_files_dropped)
        drop_layout.addWidget(self.drop_area)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        drop_layout.addLayout(btn_layout)
        
        layout.addWidget(drop_group)
        
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Whisper Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v2"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setToolTip(
            "tiny: Fastest, lower accuracy\n"
            "base: Fast, decent accuracy (recommended)\n"
            "small: Medium speed, good accuracy\n"
            "medium: Slower, very good accuracy\n"
            "large-v2: Slowest, best accuracy"
        )
        settings_layout.addWidget(self.model_combo)
        settings_layout.addStretch()
        
        layout.addWidget(settings_group)
        
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        progress_layout.addWidget(self.status_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        
        self.btn_start = QPushButton("Start Processing")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.btn_start.clicked.connect(self.start_processing)
        layout.addWidget(self.btn_start)
        
        tip = QLabel("Note: FFmpeg must be installed and added to system PATH")
        tip.setStyleSheet("color: #999; font-size: 11px;")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
    
    def on_files_dropped(self, files: list):
        added = 0
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in VideoTranslator.SUPPORTED_FORMATS:
                if f not in self.video_files:
                    self.video_files.append(f)
                    item = QListWidgetItem(f"[Video] {os.path.basename(f)}")
                    item.setToolTip(f)
                    self.drop_area.addItem(item)
                    added += 1
        
        if added > 0:
            self.log(f"Added {added} video file(s)")
        self.update_status()
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;All Files (*)"
        )
        if files:
            self.on_files_dropped(files)
    
    def clear_files(self):
        self.video_files.clear()
        self.drop_area.clear()
        self.update_status()
    
    def update_status(self):
        count = len(self.video_files)
        if count > 0:
            self.status_label.setText(f"{count} video file(s) added")
        else:
            self.status_label.setText("Ready - drag video files or folders here")
    
    def log(self, message: str):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def start_processing(self):
        if not self.video_files:
            QMessageBox.warning(self, "Warning", "Please add video files first")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.btn_start.setEnabled(False)
        self.btn_start.setText("Processing...")
        self.log_text.clear()
        
        self.worker_signals = WorkerSignals()
        self.worker_signals.progress.connect(self.on_progress)
        self.worker_signals.finished.connect(self.on_finished)
        self.worker_signals.error.connect(self.on_error)
        self.worker_signals.log.connect(self.log)
        
        model_size = self.model_combo.currentText()
        files = self.video_files.copy()
        
        thread = threading.Thread(
            target=self.process_videos,
            args=(files, model_size),
            daemon=True
        )
        thread.start()
    
    def process_videos(self, files: list, model_size: str):
        try:
            translator = VideoTranslator(self.worker_signals)
            translator.load_model(model_size)
            
            total = len(files)
            success = 0
            
            for i, video_path in enumerate(files):
                self.worker_signals.progress.emit(
                    int((i / total) * 100),
                    f"Processing ({i + 1}/{total}): {os.path.basename(video_path)}"
                )
                
                try:
                    if translator.process_video(video_path):
                        success += 1
                except Exception as e:
                    self.worker_signals.log.emit(f"Failed: {video_path}\nError: {str(e)}")
            
            self.worker_signals.progress.emit(100, "Done")
            self.worker_signals.finished.emit(f"Completed: {success}/{total} video(s) successful")
            
        except Exception as e:
            self.worker_signals.error.emit(str(e))
    
    def on_progress(self, percent: int, status: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(status)
    
    def on_finished(self, message: str):
        self.is_processing = False
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Start Processing")
        self.log(f"\n[OK] {message}")
        QMessageBox.information(self, "Done", message)
    
    def on_error(self, error: str):
        self.is_processing = False
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Start Processing")
        self.log(f"\n[ERROR] {error}")
        QMessageBox.critical(self, "Error", f"Processing error:\n{error}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
