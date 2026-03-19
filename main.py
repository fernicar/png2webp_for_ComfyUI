#!/usr/bin/env python3
"""
PNG to WebP Converter GUI Application
MVC Architecture: View and Controller components
Model: png2webp.py
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QProgressBar, QTextEdit,
    QGroupBox, QCheckBox, QSpinBox, QComboBox, QStatusBar,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

# Import the Model
import png2webp


class ConversionProcessor:
    """Processor for handling PNG to WebP conversion with responsive GUI."""
    
    def __init__(self, files: List[str], settings: dict, log_callback=None, progress_callback=None, result_callback=None, error_callback=None):
        self.files = files
        self.settings = settings
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.result_callback = result_callback
        self.error_callback = error_callback
        self._is_running = True
        self._current_index = 0
        
    def stop(self):
        self._is_running = False
        
    def process_next_file(self):
        """Process one file at a time to keep GUI responsive."""
        if not self._is_running or self._current_index >= len(self.files):
            return False  # Stop processing
            
        file_path = self.files[self._current_index]
        
        try:
            if self.log_callback:
                self.log_callback(f"Converting: {file_path}")
            
            # Convert the file
            png2webp.convert_png_to_webp(
                file_path,
                lossless=self.settings['lossless'],
                quality=self.settings['quality'],
                method=self.settings['method'],
                use_current_date=self.settings['use_current_date'],
                delete_after=self.settings['delete_after']
            )
            
            if self.result_callback:
                self.result_callback(file_path, "Success")
            if self.log_callback:
                self.log_callback(f"✓ Completed: {file_path}")
            
            # Update progress
            if self.progress_callback:
                self.progress_callback(self._current_index + 1, len(self.files))
            
            self._current_index += 1
            return True  # Continue processing
            
        except Exception as e:
            error_msg = f"✗ Error converting {file_path}: {str(e)}"
            if self.log_callback:
                self.log_callback(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
            self._current_index += 1
            return True  # Continue with next file
            


class PNG2WebPView(QMainWindow):
    """Main GUI window for PNG to WebP conversion."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG to WebP Converter")
        self.setMinimumSize(800, 600)
        
        # Initialize instance variables with proper types
        self.thread: Optional[QThread] = None
        # self.worker: Optional[ConversionWorker] = None
        self.selected_files: List[str] = []
        
        # Set Fusion style and system color scheme
        QApplication.setStyle("Fusion")
        
        # Setup UI
        self.setup_ui()
        
        # Setup logging
        self.setup_logging()
        
    def setup_ui(self):
        """Setup the main user interface."""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("PNG to WebP Converter")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Settings group
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QHBoxLayout()
        
        # Quality setting
        quality_layout = QVBoxLayout()
        quality_label = QLabel("Quality (0-100):")
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(0, 100)
        self.quality_spinbox.setValue(90)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_spinbox)
        
        # Method setting
        method_layout = QVBoxLayout()
        method_label = QLabel("Compression Method:")
        self.method_combo = QComboBox()
        self.method_combo.addItems(["0 (Fast)", "1", "2", "3", "4", "5", "6 (Better)"])
        self.method_combo.setCurrentIndex(6)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        
        # Options
        options_layout = QVBoxLayout()
        self.lossless_checkbox = QCheckBox("Lossless Compression")
        self.use_current_date_checkbox = QCheckBox("Use Current Date")
        self.delete_after_checkbox = QCheckBox("Delete Original PNG After Conversion")
        options_layout.addWidget(self.lossless_checkbox)
        options_layout.addWidget(self.use_current_date_checkbox)
        options_layout.addWidget(self.delete_after_checkbox)
        
        settings_layout.addLayout(quality_layout)
        settings_layout.addLayout(method_layout)
        settings_layout.addLayout(options_layout)
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No files selected")
        self.select_files_btn = QPushButton("Select PNG Files")
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        file_layout.addWidget(self.select_files_btn)
        file_layout.addWidget(self.select_folder_btn)
        
        # Progress area
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label = QLabel("Ready to convert")
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.convert_btn)
        button_layout.addWidget(self.stop_btn)
        
        # Results table
        results_group = QGroupBox("Conversion Results")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["File", "Status", "Details"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        
        # Log area
        log_group = QGroupBox("Conversion Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Removed maximum height limitation to allow full use of available space
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Splitter for results and log
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(results_group)
        splitter.addWidget(log_group)
        splitter.setSizes([300, 150])
        
        # Add all layouts to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(settings_group)
        main_layout.addLayout(file_layout)
        main_layout.addLayout(progress_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setup_logging(self):
        """Setup logging to display in the GUI."""
        # Clear existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Create custom handler for GUI
        class GuiLogHandler(logging.Handler):
            def __init__(self, log_widget):
                super().__init__()
                self.log_widget = log_widget
                
            def emit(self, record):
                msg = self.format(record)
                self.log_widget.append(msg)
                
        gui_handler = GuiLogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)
        
    def select_files(self):
        """Open file dialog to select PNG files."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PNG Files", "", "PNG Files (*.png);;All Files (*)"
        )
        if files:
            self.selected_files = files
            self.file_label.setText(f"Selected {len(files)} files")
            self.status_bar.showMessage(f"Selected {len(files)} files")
            
    def select_folder(self):
        """Open folder dialog to select directory with PNG files."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with PNG Files")
        if folder:
            # Find all PNG files in the folder
            png_files = list(Path(folder).rglob("*.png"))
            if png_files:
                self.selected_files = [str(f) for f in png_files]
                self.file_label.setText(f"Found {len(png_files)} PNG files in {folder}")
                self.status_bar.showMessage(f"Found {len(png_files)} PNG files in {folder}")
            else:
                QMessageBox.warning(self, "No PNG Files", "No PNG files found in the selected folder.")
                
    def start_conversion(self):
        """Start the conversion process with responsive GUI."""
        if not hasattr(self, 'selected_files') or not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select PNG files or a folder first.")
            return
            
        # Get settings
        settings = {
            'quality': self.quality_spinbox.value(),
            'method': self.method_combo.currentIndex(),
            'lossless': self.lossless_checkbox.isChecked(),
            'use_current_date': self.use_current_date_checkbox.isChecked(),
            'delete_after': self.delete_after_checkbox.isChecked()
        }
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.log_text.clear()
        
        # Create processor
        self.processor = ConversionProcessor(
            self.selected_files,
            settings,
            log_callback=self.add_log_message,
            progress_callback=self.update_progress,
            result_callback=self.add_conversion_result,
            error_callback=self.handle_error
        )
        
        # Update UI state
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage(f"Converting {len(self.selected_files)} files...")
        
        # Start timer-based processing
        self.conversion_timer = QTimer()
        self.conversion_timer.timeout.connect(self.process_next_file)
        self.conversion_timer.start(10)  # Process one file every 10ms to keep GUI responsive
        
    def process_next_file(self):
        """Process the next file in the queue."""
        should_continue = self.processor.process_next_file()
        
        if not should_continue:
            # Conversion completed or stopped
            self.conversion_timer.stop()
            self.convert_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            if self.processor._is_running:
                self.status_bar.showMessage("Conversion completed")
            else:
                self.status_bar.showMessage("Conversion stopped by user")
        
    def stop_conversion(self):
        """Stop the conversion process."""
        if hasattr(self, 'processor') and self.processor:
            self.processor.stop()
            self.status_bar.showMessage("Conversion stopped by user")
            self.convert_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
    def update_worker_progress(self, current, total, worker_id):
        """Update progress for a specific worker."""
        # Calculate overall progress
        if hasattr(self, 'total_files') and hasattr(self, 'completed_files'):
            # This is a simplified progress calculation
            # In a real implementation, you'd want to track each worker's progress more precisely
            overall_progress = int((current / total) * 100)
            self.progress_bar.setValue(overall_progress)
            self.status_label.setText(f"Worker {worker_id}: Converting {current}/{total} files")
            
    def update_progress(self, current, total):
        """Update the progress bar."""
        progress_percent = int((current / total) * 100)
        self.progress_bar.setValue(progress_percent)
        self.status_label.setText(f"Converting: {current}/{total} files")
        
        if current == total:
            self.convert_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage("Conversion completed")
            
    def add_log_message(self, message):
        """Add a message to the log."""
        self.log_text.append(message)
        
    def handle_error(self, error_message):
        """Handle conversion errors."""
        QMessageBox.critical(self, "Conversion Error", error_message)
        
    def add_conversion_result(self, input_file, status):
        """Add a conversion result to the table."""
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)
        
        file_item = QTableWidgetItem(input_file)
        status_item = QTableWidgetItem(status)
        details_item = QTableWidgetItem("Completed successfully")
        
        self.results_table.setItem(row_position, 0, file_item)
        self.results_table.setItem(row_position, 1, status_item)
        self.results_table.setItem(row_position, 2, details_item)


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application icon and style
    app.setApplicationName("PNG to WebP Converter")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    window = PNG2WebPView()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()