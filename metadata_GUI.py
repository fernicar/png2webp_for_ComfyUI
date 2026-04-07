#!/usr/bin/env python3
"""
WebP/PNG/Jpeg Metadata Viewer & Extractor GUI Application
View and extract parts of embedded ComfyUI metadata using regex patterns.
Supports capture groups for extracting specific parts of matches.
Supports selecting specific matches from files with multiple matches.
"""

import sys
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTextEdit, QGroupBox, 
    QStatusBar, QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit,
    QCheckBox, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from PIL import Image
from PIL.ExifTags import TAGS
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Debug logging toggle
DEBUG = True

def debug_log(message: str):
    """Print debug log if DEBUG is enabled."""
    if DEBUG:
        print(f"🔍 DEBUG: {message}", flush=True)


class MetadataExtractor:
    """Extracts metadata from PNG, WebP and Jpeg files."""
    
    @staticmethod
    def _extract_raw_unicode_metadata(filepath: str) -> Optional[str]:
        """
        Shared helper: Read file directly from disk and search for UNICODE UserComment.
        This bypasses PIL which corrupts/modifies EXIF bytes.
        This is the only method that actually works for Civitai files.
        """
        debug_log(f"🔧 _extract_raw_unicode_metadata() START")
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
                u_marker = b'UNICODE\x00\x00'
                u_offset = file_data.find(u_marker)
                debug_log(f"🔧 UNICODE marker found at offset: {u_offset}")
                if u_offset <= 0:
                    debug_log(f"🔧 _extract_raw_unicode_metadata() FAIL: no UNICODE marker")
                    return None
                
                user_comment_data = file_data[u_offset + len(u_marker):]
                debug_log(f"🔧 UserComment data length: {len(user_comment_data)} bytes")
                
                # CIVITAI BUG FIX: Metadata ends long before buffer ends!
                # Try progressive cutoffs until something decodes correctly
                original_length = len(user_comment_data)
                decoded = None
                used_encoding = None
                # Try cutoffs at 16kb, 8kb, 4kb, 2kb, 1kb
                for cutoff in [16384, 8192, 4096, 2048, 1024]:
                    if len(user_comment_data) > cutoff:
                        test_buffer = user_comment_data[:cutoff]
                        debug_log(f"🔧 Testing cutoff at {cutoff} bytes")
                        
                        # Try all encodings on this shorter buffer
                        for encoding in ['utf-16le', 'utf-16be', 'utf-8']:
                            try:
                                test_decoded = test_buffer.decode(encoding, errors='strict')
                                # Verify this actually looks like english text
                                if ' ' in test_decoded and any(c.islower() for c in test_decoded[:100]):
                                    decoded = test_decoded
                                    used_encoding = encoding
                                    user_comment_data = test_buffer
                                    debug_log(f"🔧 ✅ Successfully decoded with {encoding} at cutoff {cutoff}")
                                    break
                            except:
                                continue
                        
                        if decoded:
                            break
                
                # If still no success, try full buffer with replace mode
                if not decoded:
                    decoded = user_comment_data.decode('utf-16le', errors='replace')
                    debug_log(f"🔧 Fallback decoding with utf-16le replace")
                
                if not decoded:
                    debug_log(f"🔧 Fallback decoding with utf-16be replace")
                    decoded = user_comment_data.decode('utf-16be', errors='replace')
                
                decoded = decoded.rstrip('\x00')
                debug_log(f"🔧 Decoded text length: {len(decoded)}")
                debug_log(f"🔧 First 100 chars: {repr(decoded[:100])}")
                
                # Verify this looks like actual generation metadata
                valid_markers = ('Negative prompt:', 'Steps:', 'BREAK', 'Model:', 'Civitai resources', 'Created Date:')
                found_markers = [marker for marker in valid_markers if marker in decoded]
                debug_log(f"🔧 Found valid markers: {found_markers}")
                
                if decoded and any(marker in decoded for marker in valid_markers):
                    debug_log(f"🔧 ✅ VALID METADATA FOUND!")
                    return decoded
                else:
                    debug_log(f"🔧 ❌ No valid markers found")
                
                return None
        except Exception as e:
            debug_log(f"🔧 ❌ CRASH in raw reader: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _parse_civitai_parameters(parameters: str, metadata: Dict[str, str]):
        """Shared helper: Parse CivitAI/A1111 parameters string into structured fields."""
        metadata['parameters'] = parameters
        
        if 'Negative prompt:' in parameters:
            positive, _, rest = parameters.partition('Negative prompt:')
            metadata['positive_prompt'] = positive.strip()
            if 'Steps:' in rest:
                negative, _, params = rest.partition('\nSteps:')
                metadata['negative_prompt'] = negative.strip()
                if params:
                    metadata['generation_params'] = "Steps:" + params.strip()
            else:
                metadata['negative_prompt'] = rest.strip()
        elif 'Steps:' in parameters:
            positive, _, params = parameters.partition('\nSteps:')
            metadata['positive_prompt'] = positive.strip()
            metadata['generation_params'] = "Steps:" + params.strip()
        else:
            metadata['positive_prompt'] = parameters.strip()
    
    @staticmethod
    def _extract_xmp_metadata(img, metadata: Dict[str, str]):
        """Extract CivitAI metadata from XMP tags."""
        if 'XML:com.adobe.xmp' not in img.info:
            return
        
        xmp_data = img.info['XML:com.adobe.xmp']
        if isinstance(xmp_data, bytes):
            xmp_data = xmp_data.decode('utf-8', errors='replace')
        
        import re
        
        # Pattern 1: Standard dc:description with RDF li
        desc_match = re.search(r'<dc:description>(.*?)</dc:description>', xmp_data, re.DOTALL)
        if desc_match:
            desc_content = desc_match.group(1)
            prompt_match = re.search(r'<rdf:li[^>]*>(.*?)</rdf:li>', desc_content, re.DOTALL)
            if prompt_match:
                parameters = prompt_match.group(1).strip()
                parameters = parameters.replace('<', '<').replace('>', '>').replace('&', '&')
                metadata['parameters'] = parameters
        
        # Pattern 2: Direct xmp:Description with parameters attribute
        if 'parameters' not in metadata:
            param_match = re.search(r'parameters="([^"]+)"', xmp_data, re.DOTALL)
            if param_match:
                parameters = param_match.group(1)
                parameters = parameters.replace('<', '<').replace('>', '>').replace('&', '&')
                metadata['parameters'] = parameters
        
        # Pattern 3: Try any text content that looks like CivitAI prompt
        if 'parameters' not in metadata:
            if ('Steps:' in xmp_data or 'Seed:' in xmp_data or 'Civitai resources' in xmp_data):
                clean_data = re.sub(r'<[^>]+>', '', xmp_data)
                clean_data = clean_data.replace('<', '<').replace('>', '>').replace('&', '&')
                clean_data = '\n'.join([line.strip() for line in clean_data.splitlines() if line.strip()])
                if len(clean_data) > 50:
                    metadata['parameters'] = clean_data
        
        # Parse parameters if found
        if 'parameters' in metadata:
            MetadataExtractor._parse_civitai_parameters(metadata['parameters'], metadata)
    
    @staticmethod
    def _extract_exif_usercomment(exif, metadata: Dict[str, str]):
        """Extract and decode UserComment from EXIF data."""
        user_comment_tag = 37510
        value = None
        
        if user_comment_tag in exif:
            value = exif[user_comment_tag]
        if not isinstance(value, bytes):
            return
        
        try:
            if value.startswith(b'ASCII\x00\x00\x00'):
                value = value[8:].decode('ascii', errors='replace')
            elif value.startswith(b'UNICODE\x00'):
                # Try both endians for UNICODE
                try:
                    value = value[8:].decode('utf-16be', errors='replace')
                except:
                    try:
                        value = value[8:].decode('utf-16le', errors='replace')
                    except:
                        value = value[8:].decode('utf-8', errors='replace')
            elif value.startswith(b'UTF8\x00\x00\x00'):
                value = value[8:].decode('utf-8', errors='replace')
            else:
                # Try all encodings in order
                try:
                    value = value.decode('utf-16be', errors='replace')
                except:
                    try:
                        value = value.decode('utf-16le', errors='replace')
                    except:
                        value = value.decode('utf-8', errors='replace')
        except:
            value = str(value)
        
        # Validate and parse
        if isinstance(value, str):
            valid_markers = ('Negative prompt:', 'Steps:', 'BREAK', 'Civitai resources')
            if any(marker in value for marker in valid_markers):
                MetadataExtractor._parse_civitai_parameters(value, metadata)
    
    @staticmethod
    def _extract_civitai_exif_fallback(exif, metadata: Dict[str, str]):
        """Extract CivitAI metadata from EXIF tags as final fallback."""
        if 'parameters' in metadata:
            return
        
        MetadataExtractor._extract_exif_usercomment(exif, metadata)
        
        # Check remaining EXIF tags
        for tag_id, value in exif.items():
            if tag_id == 37510:
                continue
            if not isinstance(value, str):
                continue
            
            valid_markers = ('Negative prompt:', 'Steps:', 'BREAK', 'Model:', 'Civitai resources')
            if any(marker in value for marker in valid_markers):
                MetadataExtractor._parse_civitai_parameters(value, metadata)
                break
    
    @staticmethod
    def _extract_comfyui_exif(exif, metadata: Dict[str, str]):
        """Extract ComfyUI formatted metadata from EXIF tags."""
        for tag_id, value in exif.items():
            tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
            
            if isinstance(value, str):
                if value.startswith("Prompt:"):
                    json_str = value[7:]
                    try:
                        parsed = json.loads(json_str)
                        metadata['prompt'] = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, TypeError):
                        metadata['prompt'] = json_str
                elif value.startswith("Workflow:"):
                    json_str = value[9:]
                    try:
                        parsed = json.loads(json_str)
                        metadata['workflow'] = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, TypeError):
                        metadata['workflow'] = json_str
                else:
                    if ':' in value:
                        key, _, json_str = value.partition(':')
                        try:
                            parsed = json.loads(json_str)
                            metadata[key] = json.dumps(parsed, indent=2, ensure_ascii=False)
                        except (json.JSONDecodeError, TypeError):
                            metadata[key] = json_str
                    else:
                        metadata[tag_name] = str(value)
            else:
                metadata[tag_name] = str(value)
    
    @staticmethod
    def extract_from_png(filepath: str, method: str = "comfyui") -> Dict[str, str]:
        """Extract metadata from a PNG file."""
        metadata = {}
        try:
            with Image.open(filepath) as img:
                info = img.info
                
                if method == "civitai":
                    # First use the working raw disk reader
                    raw_metadata = MetadataExtractor._extract_raw_unicode_metadata(filepath)
                    if raw_metadata:
                        MetadataExtractor._parse_civitai_parameters(raw_metadata, metadata)
                    
                    # Fallback to direct parameters key
                    if 'parameters' not in metadata and 'parameters' in info:
                        MetadataExtractor._parse_civitai_parameters(info['parameters'], metadata)
                    # DO NOT FALLBACK TO COMFYUI HERE - we still need to check EXIF UserComment!
                
                if method == "comfyui":
                    # ComfyUI format
                    for key, value in info.items():
                        if isinstance(value, bytes):
                            # Decode bytes before trying to parse
                            try:
                                value = value.decode('utf-8', errors='replace')
                            except:
                                value = str(value)
                        
                        if key in ('prompt', 'workflow'):
                            try:
                                parsed = json.loads(value)
                                metadata[key] = json.dumps(parsed, indent=2, ensure_ascii=False)
                            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                                metadata[key] = value
                        else:
                            try:
                                parsed = json.loads(value)
                                metadata[key] = json.dumps(parsed, indent=2, ensure_ascii=False)
                            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                                metadata[key] = str(value)
                
                # Always check EXIF for UserComment even in PNG files (CivitAI sometimes puts it here)
                exif = img.getexif()
                MetadataExtractor._extract_exif_usercomment(exif, metadata)
        except Exception as e:
            # Don't fail the whole extraction, just log error and return what we have
            import traceback
            traceback.print_exc()
            if not metadata:
                metadata['error'] = f"Error reading PNG metadata: {str(e)}"
        return metadata
    
    @staticmethod
    def extract_from_webp(filepath: str, method: str = "comfyui") -> Dict[str, str]:
        """Extract metadata from a WebP and Jpeg file (stored in EXIF tags)."""
        metadata = {}
        try:
            with Image.open(filepath) as img:
                # Extraction priority order (most reliable first)
                if method == "civitai":
                    # 1. Raw disk reader (THE ONLY ONE THAT ACTUALLY WORKS)
                    raw_metadata = MetadataExtractor._extract_raw_unicode_metadata(filepath)
                    if raw_metadata:
                        MetadataExtractor._parse_civitai_parameters(raw_metadata, metadata)
                    
                    # 2. XMP metadata (newer CivitAI images)
                    MetadataExtractor._extract_xmp_metadata(img, metadata)
                    
                    # 3. EXIF fallback
                    exif = img.getexif()
                    MetadataExtractor._extract_civitai_exif_fallback(exif, metadata)
                else:
                    # ComfyUI format
                    exif = img.getexif()
                    MetadataExtractor._extract_comfyui_exif(exif, metadata)
                        
        except Exception as e:
            metadata['error'] = f"Error reading WebP or Jpeg metadata: {str(e)}"
        return metadata
    
    @staticmethod
    def extract(filepath: str, method: str = "comfyui") -> Dict[str, str]:
        """Extract metadata from either PNG, WebP or Jpeg file."""
        # First detect actual file format (not just extension)
        try:
            debug_log(f"🎯 START extract() file={filepath} method={method}")
            
            with Image.open(filepath) as img:
                actual_format = img.format.lower() if img.format is not None else Path(filepath).suffix.lower().lstrip('.')
                debug_log(f"📌 PIL detected actual format: {actual_format} (file extension: {Path(filepath).suffix})")
                
                if actual_format == 'png':
                    debug_log(f"➡️  Calling extract_from_png()")
                    result = MetadataExtractor.extract_from_png(filepath, method)
                elif actual_format in ('webp', 'jpeg', 'jpg'):
                    debug_log(f"➡️  Calling extract_from_webp()")
                    result = MetadataExtractor.extract_from_webp(filepath, method)
                else:
                    result = {'error': f"Unsupported file format: {actual_format}"}
                
                debug_log(f"✅ EXTRACT COMPLETE. Found keys: {list(result.keys())}")
                return result
        except Exception as e:
            debug_log(f"❌ extract() FAILED: {str(e)}")
            return {'error': f"Error opening file: {str(e)}"}
    
    @staticmethod
    def get_full_metadata(filepath: str, method: str = "comfyui") -> str:
        """Get all metadata as a single string for regex searching."""
        metadata = MetadataExtractor.extract(filepath, method)
        result = ""
        for key, value in metadata.items():
            result += f"{key}: {value}\n"
        return result


class MetadataViewerView(QMainWindow):
    """Main GUI window for viewing and extracting metadata."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG/WebP/Jpeg Metadata Viewer & Extractor")
        self.setMinimumSize(1200, 700)
        
        self.selected_files: List[str] = []
        self.current_metadata: Dict[str, str] = {}
        self.current_file: str = ""
        self.regex_matches: Dict[str, List[str]] = {}  # file -> list of matches
        self.current_file_matches: List[str] = []  # matches for current file
        
        # Set Fusion style
        QApplication.setStyle("Fusion")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main user interface."""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Compact header
        header_layout = QHBoxLayout()
        title_label = QLabel("Metadata Viewer & Extractor")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Extraction method toggle
        header_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItem("ComfyUI (default)", "comfyui")
        self.method_combo.addItem("CivitAI / A1111", "civitai")
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        header_layout.addWidget(self.method_combo)
        
        header_layout.addStretch()
        self.file_info_label = QLabel("No files loaded")
        header_layout.addWidget(self.file_info_label)
        
        # File selection buttons
        file_btn_layout = QHBoxLayout()
        file_btn_layout.setSpacing(5)
        self.select_files_btn = QPushButton("Select Files")
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        
        file_btn_layout.addWidget(self.select_files_btn)
        file_btn_layout.addWidget(self.select_folder_btn)
        file_btn_layout.addStretch()
        file_btn_layout.addWidget(self.clear_btn)
        
        # Main vertical splitter: regex panel on top, metadata viewer below
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top panel - Regex Pattern Extractor
        regex_group = QGroupBox("Regex Pattern Extractor")
        regex_layout = QVBoxLayout()
        regex_layout.setContentsMargins(5, 5, 5, 5)
        
        # Regex input row
        regex_input_layout = QHBoxLayout()
        regex_input_layout.addWidget(QLabel("Pattern:"))
        self.regex_input = QLineEdit()
        self.regex_input.setPlaceholderText("Enter regex pattern or select a preset...")
        self.regex_input.textChanged.connect(self.on_regex_changed)
        regex_input_layout.addWidget(self.regex_input)
        
        self.regex_case_checkbox = QCheckBox("Case Sensitive")
        self.regex_case_checkbox.setChecked(True)
        self.regex_case_checkbox.stateChanged.connect(self.on_regex_changed)
        regex_input_layout.addWidget(self.regex_case_checkbox)
        
        regex_layout.addLayout(regex_input_layout)
        
        # Preset patterns row
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Select a pattern --", "")
        self.preset_combo.addItem('"text" (full match)', '"text":\\s*"[^"]*"')
        self.preset_combo.addItem('"text" (content only)', '"text":\\s*"([^"]*)"')
        self.preset_combo.addItem('prompt (full match)', '"prompt":\\s*\\{[^}]*\\}')
        self.preset_combo.addItem('prompt (content only)', '"prompt":\\s*(\\{[^}]*\\})')
        self.preset_combo.addItem('positive prompt', 'positive.*?prompt')
        self.preset_combo.addItem('negative prompt', 'negative.*?prompt')
        self.preset_combo.addItem('seed (full)', '"seed":\\s*\\d+')
        self.preset_combo.addItem('seed (value only)', '"seed":\\s*(\\d+)')
        self.preset_combo.addItem('steps (full)', '"steps":\\s*\\d+')
        self.preset_combo.addItem('steps (value only)', '"steps":\\s*(\\d+)')
        self.preset_combo.addItem('cfg (full)', '"cfg":\\s*[\\d.]+')
        self.preset_combo.addItem('cfg (value only)', '"cfg":\\s*([\\d.]+)')
        self.preset_combo.addItem('sampler (full)', '"sampler_name":\\s*"[^"]*"')
        self.preset_combo.addItem('sampler (name only)', '"sampler_name":\\s*"([^"]*)"')
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        regex_layout.addLayout(preset_layout)
        
        # Capture group options row
        group_layout = QHBoxLayout()
        self.use_group_checkbox = QCheckBox("Use capture group")
        self.use_group_checkbox.stateChanged.connect(self.on_regex_changed)
        group_layout.addWidget(self.use_group_checkbox)
        
        group_layout.addWidget(QLabel("Group #:"))
        self.group_spinbox = QSpinBox()
        self.group_spinbox.setRange(1, 10)
        self.group_spinbox.setValue(1)
        self.group_spinbox.valueChanged.connect(self.on_regex_changed)
        group_layout.addWidget(self.group_spinbox)
        
        group_layout.addWidget(QLabel("(extracts only the captured group content)"))
        group_layout.addStretch()
        regex_layout.addLayout(group_layout)
        
        # Match selection row - for selecting specific match from current file
        match_select_layout = QHBoxLayout()
        self.use_match_index_checkbox = QCheckBox("Use specific match from current file")
        self.use_match_index_checkbox.stateChanged.connect(self.on_match_selection_changed)
        match_select_layout.addWidget(self.use_match_index_checkbox)
        
        match_select_layout.addWidget(QLabel("Match #:"))
        self.match_index_combo = QComboBox()
        self.match_index_combo.setMinimumWidth(150)
        self.match_index_combo.currentIndexChanged.connect(self.on_match_selection_changed)
        match_select_layout.addWidget(self.match_index_combo)
        
        match_select_layout.addWidget(QLabel("(select which match to save, saves without suffix)"))
        match_select_layout.addStretch()
        regex_layout.addLayout(match_select_layout)
        
        # Regex match preview
        regex_layout.addWidget(QLabel("Match Preview (current file):"))
        self.regex_preview = QTextEdit()
        self.regex_preview.setReadOnly(True)
        self.regex_preview.setFont(QFont("Consolas", 10))
        self.regex_preview.setMinimumHeight(80)
        self.regex_preview.setMaximumHeight(150)
        regex_layout.addWidget(self.regex_preview)
        
        # File conflict handling row
        conflict_layout = QHBoxLayout()
        conflict_layout.addWidget(QLabel("If .txt file exists:"))
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Skip - don't overwrite")
        self.conflict_combo.addItem("Overwrite - replace existing")
        self.conflict_combo.addItem("Prepend - add before existing content")
        self.conflict_combo.addItem("Append - add after existing content")
        conflict_layout.addWidget(self.conflict_combo)
        conflict_layout.addStretch()
        regex_layout.addLayout(conflict_layout)
        
        # Extract buttons
        extract_layout = QHBoxLayout()
        self.extract_preview_btn = QPushButton("Preview All Matches")
        self.extract_preview_btn.clicked.connect(self.preview_all_matches)
        self.extract_save_btn = QPushButton("Save Matches to TXT Files")
        self.extract_save_btn.clicked.connect(self.save_matches_to_files)
        self.extract_save_btn.setEnabled(False)
        
        extract_layout.addWidget(self.extract_preview_btn)
        extract_layout.addWidget(self.extract_save_btn)
        extract_layout.addStretch()
        
        regex_layout.addLayout(extract_layout)
        regex_group.setLayout(regex_layout)
        
        # Bottom horizontal splitter: file list | metadata
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - File list
        left_panel = QGroupBox("Files")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(2, 2, 2, 2)
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        left_layout.addWidget(self.file_list)
        left_panel.setLayout(left_layout)
        
        # Right panel - Metadata display
        right_panel = QGroupBox("Metadata")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(2, 2, 2, 2)
        
        self.metadata_tabs = QTabWidget()
        
        self.parsed_text = QTextEdit()
        self.parsed_text.setReadOnly(True)
        self.parsed_text.setFont(QFont("Consolas", 10))
        self.metadata_tabs.addTab(self.parsed_text, "Parsed Data")
        
        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderLabels(["Key", "Value Preview"])
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_view.itemClicked.connect(self.on_tree_item_clicked)
        self.metadata_tabs.addTab(self.tree_view, "Tree View")
        
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Consolas", 9))
        self.metadata_tabs.addTab(self.raw_text, "Raw Data")
        
        self.all_matches_text = QTextEdit()
        self.all_matches_text.setReadOnly(True)
        self.all_matches_text.setFont(QFont("Consolas", 10))
        self.metadata_tabs.addTab(self.all_matches_text, "All Matches")
        
        right_layout.addWidget(self.metadata_tabs)
        right_panel.setLayout(right_layout)
        
        bottom_splitter.addWidget(left_panel)
        bottom_splitter.addWidget(right_panel)
        bottom_splitter.setSizes([200, 800])
        
        # Add to main splitter
        main_splitter.addWidget(regex_group)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([350, 350])
        
        # Add all to main layout
        main_layout.addLayout(header_layout)
        main_layout.addLayout(file_btn_layout)
        main_layout.addWidget(main_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select PNG or WebP files to view metadata")
        
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PNG/WebP Files", "", 
            "Image Files (*.png *.webp *.jpeg *.jpg);;PNG Files (*.png);;WebP Files (*.webp);;Jpeg Files (*.jpeg *.jpg);;All Files (*)"
        )
        if files:
            self.add_files(files)
            
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Image Files")
        if folder:
            image_files = list(Path(folder).rglob("*.png")) + list(Path(folder).rglob("*.webp")) + list(Path(folder).rglob("*.jpeg")) + list(Path(folder).rglob("*.jpg"))
            if image_files:
                self.add_files([str(f) for f in sorted(image_files)])
            else:
                QMessageBox.warning(self, "No Image Files", 
                    "No PNG, WebP or Jpeg files found in the selected folder.")
                
    def add_files(self, files: List[str]):
        for f in files:
            if f not in self.selected_files:
                self.selected_files.append(f)
                item = QListWidgetItem(Path(f).name)
                item.setToolTip(f)
                self.file_list.addItem(item)
        
        self.file_info_label.setText(f"{len(self.selected_files)} file(s)")
        self.status_bar.showMessage(f"Added {len(files)} file(s)")
        
        if self.file_list.count() > 0 and not self.file_list.currentItem():
            self.file_list.setCurrentRow(0)
            
    def on_file_selected(self, item: QListWidgetItem):
        filepath = item.toolTip()
        self.current_file = filepath
        self.load_metadata(filepath)
        
    def load_metadata(self, filepath: str):
        self.status_bar.showMessage(f"Loading: {Path(filepath).name}")
        
        method = self.method_combo.currentData()
        self.current_metadata = MetadataExtractor.extract(filepath, method)
        
        self.update_parsed_view()
        self.update_tree_view()
        self.update_raw_view(filepath)
        self.on_regex_changed()
        
        self.status_bar.showMessage(f"Loaded: {Path(filepath).name}")
        
    def update_parsed_view(self):
        self.parsed_text.clear()
        
        if 'error' in self.current_metadata:
            self.parsed_text.setTextColor(Qt.GlobalColor.red)
            self.parsed_text.append(self.current_metadata['error'])
            return
        
        if not self.current_metadata or 'info' in self.current_metadata:
            self.parsed_text.append(self.current_metadata.get('info', 'No metadata found'))
            return
        
        # First display CivitAI / A1111 format data if present
        civitai_keys = ['parameters', 'positive_prompt', 'negative_prompt', 'generation_params']
        for key in civitai_keys:
            if key in self.current_metadata:
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(f"  {key.upper()}")
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(self.current_metadata[key])
                self.parsed_text.append("")
        
        # Then display ComfyUI format data
        for key in ['prompt', 'workflow']:
            if key in self.current_metadata:
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(f"  {key.upper()}")
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(self.current_metadata[key])
                self.parsed_text.append("")
        
        # Then display all other remaining keys
        for key, value in self.current_metadata.items():
            if key not in civitai_keys + ['prompt', 'workflow', 'error', 'info']:
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(f"  {key.upper()}")
                self.parsed_text.append(f"{'='*60}")
                self.parsed_text.append(value)
                self.parsed_text.append("")
                
    def update_tree_view(self):
        self.tree_view.clear()
        
        if 'error' in self.current_metadata:
            item = QTreeWidgetItem([self.current_metadata['error'], ''])
            self.tree_view.addTopLevelItem(item)
            return
        
        if not self.current_metadata or 'info' in self.current_metadata:
            item = QTreeWidgetItem([self.current_metadata.get('info', 'No metadata'), ''])
            self.tree_view.addTopLevelItem(item)
            return
        
        for key, value in self.current_metadata.items():
            if key in ('error', 'info'):
                continue
            preview = value[:100] + ('...' if len(value) > 100 else '')
            item = QTreeWidgetItem([key, preview])
            self.tree_view.addTopLevelItem(item)
            
    def update_raw_view(self, filepath: str):
        self.raw_text.clear()
        
        self.raw_text.append(f"File: {filepath}")
        self.raw_text.append(f"Size: {Path(filepath).stat().st_size:,} bytes")
        self.raw_text.append(f"Type: {Path(filepath).suffix.upper()}")
        self.raw_text.append("")
        self.raw_text.append("-" * 60)
        self.raw_text.append("Extracted Metadata:")
        self.raw_text.append("-" * 60)
        
        for key, value in self.current_metadata.items():
            self.raw_text.append(f"\n[{key}]:")
            self.raw_text.append(value[:500] + ('...' if len(value) > 500 else ''))
            
    def on_method_changed(self):
        """Handle extraction method change."""
        if self.current_file:
            self.load_metadata(self.current_file)
        self.on_regex_changed()
    
    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        key = item.text(0)
        if key in self.current_metadata:
            self.parsed_text.clear()
            self.parsed_text.append(f"{'='*60}")
            self.parsed_text.append(f"  {key.upper()}")
            self.parsed_text.append(f"{'='*60}")
            self.parsed_text.append(self.current_metadata[key])
            self.metadata_tabs.setCurrentIndex(0)
    
    def on_preset_changed(self, index: int):
        pattern = self.preset_combo.itemData(index)
        if pattern:
            self.regex_input.setText(pattern)
            # Auto-enable capture group if pattern has groups
            has_group = '(' in pattern and ')' in pattern
            self.use_group_checkbox.setChecked(has_group)
    
    def _extract_match_text(self, match) -> str:
        """Extract the appropriate text from a regex match based on settings."""
        if self.use_group_checkbox.isChecked():
            group_num = self.group_spinbox.value()
            try:
                result = match.group(group_num)
                return result if result is not None else f"(group {group_num} not matched)"
            except IndexError:
                return f"(group {group_num} not found in match)"
        else:
            return match.group(0)
    
    def _update_match_index_combo(self):
        """Update the match index combo box based on current file matches."""
        self.match_index_combo.clear()
        
        if not self.current_file_matches:
            self.match_index_combo.addItem("(no matches)")
            self.match_index_combo.setEnabled(False)
        else:
            for i, match_text in enumerate(self.current_file_matches, 1):
                preview = match_text[:50] + ('...' if len(match_text) > 50 else '')
                self.match_index_combo.addItem(f"{i}: {preview}", i)
            self.match_index_combo.setEnabled(True)
    
    def on_match_selection_changed(self):
        """Handle changes to match selection."""
        # Update preview to show selected match
        if self.use_match_index_checkbox.isChecked() and self.current_file_matches:
            idx = self.match_index_combo.currentData()
            if idx and idx <= len(self.current_file_matches):
                match_text = self.current_file_matches[idx - 1]
                self.regex_preview.setPlainText(f"Selected match {idx}:\n\n{match_text}")
    
    def on_regex_changed(self):
        pattern = self.regex_input.text().strip()
        
        if not pattern or not self.current_file:
            self.regex_preview.setPlainText("Enter a regex pattern and select a file to see matches.")
            self.extract_save_btn.setEnabled(False)
            self.current_file_matches = []
            self._update_match_index_combo()
            return
        
        try:
            case_sensitive = self.regex_case_checkbox.isChecked()
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags | re.DOTALL)
            
            method = self.method_combo.currentData()
            full_metadata = MetadataExtractor.get_full_metadata(self.current_file, method)
            matches = list(regex.finditer(full_metadata))
            
            # Update current file matches
            self.current_file_matches = [self._extract_match_text(m) for m in matches]
            self._update_match_index_combo()
            
            if matches:
                result = f"Found {len(matches)} match(es) in {Path(self.current_file).name}:\n\n"
                for i, match in enumerate(matches, 1):
                    match_str = self._extract_match_text(match)
                    result += f"--- Match {i} ---\n"
                    result += match_str[:500] + ('...' if len(match_str) > 500 else '')
                    result += "\n\n"
                self.regex_preview.setPlainText(result)
                self.extract_save_btn.setEnabled(True)
            else:
                self.regex_preview.setPlainText("No matches found.")
                self.extract_save_btn.setEnabled(False)
                
        except re.error as e:
            self.regex_preview.setPlainText(f"Invalid regex: {str(e)}")
            self.extract_save_btn.setEnabled(False)
            self.current_file_matches = []
            self._update_match_index_combo()
    
    def preview_all_matches(self):
        pattern = self.regex_input.text().strip()
        
        if not pattern:
            QMessageBox.warning(self, "No Pattern", "Please enter a regex pattern first.")
            return
        
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select files first.")
            return
        
        try:
            case_sensitive = self.regex_case_checkbox.isChecked()
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags | re.DOTALL)
        except re.error as e:
            QMessageBox.critical(self, "Invalid Regex", f"Invalid regex pattern: {str(e)}")
            return
        
        self.all_matches_text.clear()
        self.regex_matches.clear()
        
        total_matches = 0
        files_with_matches = 0
        
        method = self.method_combo.currentData()
        for filepath in self.selected_files:
            full_metadata = MetadataExtractor.get_full_metadata(filepath, method)
            matches = list(regex.finditer(full_metadata))
            
            if matches:
                files_with_matches += 1
                match_texts = [self._extract_match_text(m) for m in matches]
                self.regex_matches[filepath] = match_texts
                total_matches += len(matches)
                
                self.all_matches_text.append(f"{'='*70}")
                self.all_matches_text.append(f"  {Path(filepath).name} ({len(matches)} match(es))")
                self.all_matches_text.append(f"{'='*70}")
                for i, match_str in enumerate(match_texts, 1):
                    self.all_matches_text.append(f"  [{i}] {match_str[:300]}{'...' if len(match_str) > 300 else ''}")
                self.all_matches_text.append("")
        
        self.all_matches_text.append(f"\n{'='*70}")
        self.all_matches_text.append(f"Summary: {files_with_matches}/{len(self.selected_files)} files matched, {total_matches} total matches")
        
        self.metadata_tabs.setCurrentIndex(3)
        self.status_bar.showMessage(f"Preview: {files_with_matches}/{len(self.selected_files)} files matched")
    
    def save_matches_to_files(self):
        pattern = self.regex_input.text().strip()
        
        if not pattern:
            QMessageBox.warning(self, "No Pattern", "Please enter a regex pattern first.")
            return
        
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select files first.")
            return
        
        try:
            case_sensitive = self.regex_case_checkbox.isChecked()
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags | re.DOTALL)
        except re.error as e:
            QMessageBox.critical(self, "Invalid Regex", f"Invalid regex pattern: {str(e)}")
            return
        
        saved_count = 0
        skipped_count = 0
        
        # Check if we're using specific match selection
        use_specific_match = self.use_match_index_checkbox.isChecked()
        selected_match_idx = None
        if use_specific_match:
            selected_match_idx = self.match_index_combo.currentData()
            if not selected_match_idx:
                QMessageBox.warning(self, "No Match Selected", 
                    "Please select a match number from the dropdown, or uncheck 'Use specific match'.")
                return
        
        # Get conflict handling mode
        conflict_mode = self.conflict_combo.currentIndex()  # 0=skip, 1=overwrite, 2=prepend, 3=append
        
        method = self.method_combo.currentData()
        for filepath in self.selected_files:
            full_metadata = MetadataExtractor.get_full_metadata(filepath, method)
            matches = list(regex.finditer(full_metadata))
            
            if matches:
                match_texts = [self._extract_match_text(m) for m in matches]
                
                base_name = Path(filepath).stem
                parent_dir = Path(filepath).parent
                
                if use_specific_match and selected_match_idx:
                    # Save only the selected match index (1-based)
                    if selected_match_idx <= len(match_texts):
                        output_path = parent_dir / f"{base_name}.txt"
                        new_content = match_texts[selected_match_idx - 1]
                        if self._save_with_conflict_handling(output_path, new_content, conflict_mode):
                            saved_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1  # File doesn't have that many matches
                elif len(match_texts) == 1:
                    # Single match: save as image.txt
                    output_path = parent_dir / f"{base_name}.txt"
                    new_content = match_texts[0]
                    if self._save_with_conflict_handling(output_path, new_content, conflict_mode):
                        saved_count += 1
                    else:
                        skipped_count += 1
                else:
                    # Multiple matches: save as image_1.txt, image_2.txt, etc.
                    for i, match_text in enumerate(match_texts, 1):
                        output_path = parent_dir / f"{base_name}_{i}.txt"
                        if self._save_with_conflict_handling(output_path, match_text, conflict_mode):
                            saved_count += 1
                        else:
                            skipped_count += 1
            else:
                skipped_count += 1
        
        self.status_bar.showMessage(f"Saved: {saved_count} files, Skipped: {skipped_count} files (no matches)")
        QMessageBox.information(self, "Save Complete", 
            f"Saved {saved_count} TXT files\nSkipped {skipped_count} files (no matches)")
            
    def _save_with_conflict_handling(self, output_path: Path, new_content: str, conflict_mode: int) -> bool:
        """
        Save content to file with conflict handling.
        
        Args:
            output_path: Path to save the file
            new_content: Content to save
            conflict_mode: 0=skip, 1=overwrite, 2=prepend, 3=append
            
        Returns:
            True if file was saved, False otherwise
        """
        try:
            if output_path.exists():
                if conflict_mode == 0:  # Skip
                    return False
                elif conflict_mode == 1:  # Overwrite
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    return True
                elif conflict_mode == 2:  # Prepend
                    with open(output_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(new_content + "\n" + existing_content)
                    return True
                elif conflict_mode == 3:  # Append
                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write("\n" + new_content)
                    return True
                else:
                    # Unknown conflict mode, treat as skip
                    return False
            else:
                # File doesn't exist, just create it
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
        except Exception as e:
            self.status_bar.showMessage(f"Error saving {output_path.name}: {str(e)}")
            return False
    
    def clear_all(self):
        self.selected_files.clear()
        self.current_metadata.clear()
        self.current_file = ""
        self.regex_matches.clear()
        self.current_file_matches.clear()
        self.file_list.clear()
        self.parsed_text.clear()
        self.tree_view.clear()
        self.raw_text.clear()
        self.regex_preview.clear()
        self.all_matches_text.clear()
        self.regex_input.clear()
        self.preset_combo.setCurrentIndex(0)
        self.use_group_checkbox.setChecked(False)
        self.group_spinbox.setValue(1)
        self.use_match_index_checkbox.setChecked(False)
        self.match_index_combo.clear()
        self.match_index_combo.setEnabled(False)
        self.file_info_label.setText("No files loaded")
        self.extract_save_btn.setEnabled(False)
        self.status_bar.showMessage("Cleared - Ready to load files")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PNG/WebP/Jpeg Metadata Viewer & Extractor")
    app.setApplicationVersion("1.0.0")
    
    window = MetadataViewerView()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()