# main.py - Photo Booth Main Application
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import cv2
import threading
import time
import os
import json
import logging
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cups
import shutil
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # Use relative path for config file to work on different systems
        self.config_path = Path('./config/settings.json')
        self.default_config = {
            "camera": {
                "resolution": [1920, 1080],
                "preview_resolution": [1280, 720],
                "fps": 30,
                "device_id": 0
            },
            "ui": {
                "fullscreen": False,
                "button_size": "large",
                "theme": "dark",
                "countdown_time": 3
            },
            "printing": {
                "default_copies": 1,
                "max_copies": 5,
                "paper_size": "4x6",
                "printer_name": "Canon_Printer"
            },
            "storage": {
                "max_local_photos": 100,
                "auto_sync": True,
                "originals_path": "./captured_photos/originals",
                "framed_path": "./captured_photos/framed",
                "sync_path": "./google_drive_sync"
            },
            "frames": {
                "default_frame": "classic_frame.png",
                "frames_path": "./assets/frames"
            },
            "logs": {
                "log_path": "./logs/photobooth.log"
            }
        }
        self.load_config()
    
    def load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self.default_config.copy()
                self.save_config()
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self.config = self.default_config.copy()
    
    def save_config(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def get(self, section, key=None):
        if key:
            return self.config.get(section, {}).get(key)
        return self.config.get(section, {})
    
    def setup_logging(self):
        """Configure logging based on config settings"""
        log_path = self.get("logs", "log_path") or "./logs/photobooth.log"
        
        # Ensure log directory exists
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )

class CameraManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.cap = None
        self.preview_running = False
        self.current_frame = None
        self.initialize_camera()
    
    def initialize_camera(self):
        try:
            device_id = self.config.get("camera", "device_id")
            self.cap = cv2.VideoCapture(device_id)
            
            # Set camera properties
            preview_res = self.config.get("camera", "preview_resolution")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, preview_res[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, preview_res[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.config.get("camera", "fps"))
            
            # Enable autofocus if available
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            logging.info("Camera initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Camera initialization failed: {e}")
            return False
    
    def start_preview(self):
        self.preview_running = True
    
    def stop_preview(self):
        self.preview_running = False
    
    def get_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                return cv2.flip(frame, 1)  # Mirror the image
        return None
    
    def capture_photo(self):
        try:
            if self.cap and self.cap.isOpened():
                # Set high resolution for capture
                capture_res = self.config.get("camera", "resolution")
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, capture_res[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, capture_res[1])
                
                # Take the photo
                ret, frame = self.cap.read()
                if ret:
                    # Flip the image horizontally (mirror effect)
                    frame = cv2.flip(frame, 1)
                    
                    # Reset to preview resolution
                    preview_res = self.config.get("camera", "preview_resolution")
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, preview_res[0])
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, preview_res[1])
                    
                    return frame
        except Exception as e:
            logging.error(f"Photo capture failed: {e}")
        return None
    
    def release(self):
        if self.cap:
            self.cap.release()

class ImageProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        
    def save_original(self, cv_image, filename):
        try:
            originals_path = Path(self.config.get("storage", "originals_path"))
            originals_path.mkdir(parents=True, exist_ok=True)
            
            filepath = originals_path / filename
            cv2.imwrite(str(filepath), cv_image)
            
            # Also save to sync folder
            sync_path = Path(self.config.get("storage", "sync_path")) / "originals"
            sync_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, sync_path / filename)
            
            return filepath
        except Exception as e:
            logging.error(f"Error saving original: {e}")
            return None
    
    def apply_frame_and_save(self, cv_image, filename, frame_name=None):
        try:
            # Convert CV2 image to PIL
            pil_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Load and apply frame
            if frame_name:
                frame_path = Path(self.config.get("frames", "frames_path")) / frame_name
                if frame_path.exists():
                    pil_image = self.apply_frame(pil_image, frame_path)
            
            # Save framed version
            framed_path = Path(self.config.get("storage", "framed_path"))
            framed_path.mkdir(parents=True, exist_ok=True)
            
            filepath = framed_path / filename
            pil_image.save(filepath, "JPEG", quality=95)
            
            # Also save to sync folder
            sync_path = Path(self.config.get("storage", "sync_path")) / "framed"
            sync_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, sync_path / filename)
            
            return filepath, pil_image
        except Exception as e:
            logging.error(f"Error applying frame: {e}")
            return None, None
    
    def apply_frame(self, image, frame_path):
        try:
            # Load frame
            frame = Image.open(frame_path).convert("RGBA")
            
            # Resize image to fit within frame (assuming frame has transparent center)
            img_width, img_height = image.size
            frame_width, frame_height = frame.size
            
            # Calculate scaling to fit image in frame
            scale = min(frame_width * 0.8 / img_width, frame_height * 0.8 / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create composite
            composite = Image.new("RGBA", (frame_width, frame_height), (255, 255, 255, 255))
            
            # Center the image
            x_offset = (frame_width - new_width) // 2
            y_offset = (frame_height - new_height) // 2
            composite.paste(resized_image, (x_offset, y_offset))
            
            # Apply frame
            composite.paste(frame, (0, 0), frame)
            
            return composite.convert("RGB")
        except Exception as e:
            logging.error(f"Error applying frame overlay: {e}")
            return image
    
    def prepare_for_print(self, image_path):
        try:
            # Open image and resize for 4x6 printing (300 DPI)
            image = Image.open(image_path)
            
            # 4x6 inches at 300 DPI = 1200x1800 pixels
            print_size = (1200, 1800)
            
            # Resize maintaining aspect ratio
            image.thumbnail(print_size, Image.Resampling.LANCZOS)
            
            # Create white background
            print_image = Image.new("RGB", print_size, (255, 255, 255))
            
            # Center the image
            x_offset = (print_size[0] - image.size[0]) // 2
            y_offset = (print_size[1] - image.size[1]) // 2
            print_image.paste(image, (x_offset, y_offset))
            
            return print_image
        except Exception as e:
            logging.error(f"Error preparing image for print: {e}")
            return None

class PrintManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.conn = None
        self.setup_printer()
    
    def setup_printer(self):
        try:
            self.conn = cups.Connection()
            printers = self.conn.getPrinters()
            logging.info(f"Available printers: {list(printers.keys())}")
            
            # Log capabilities for the configured printer
            printer_name = self.config.get("printing", "printer_name")
            if printer_name in printers:
                self.get_printer_capabilities(printer_name)
                self.get_printer_media_sizes(printer_name)
            
            return True
        except Exception as e:
            logging.error(f"Printer setup failed: {e}")
            return False
    
    def print_image(self, image_path, copies=1):
        try:
            if not self.conn:
                logging.error("No CUPS connection available")
                return False
            
            # First, clear any stuck jobs to ensure clean state
            logging.info("Clearing any stuck print jobs before printing...")
            self.clear_print_queue()
            
            # Try system lp command as fallback for Canon MG3600
            printer_name = self.config.get("printing", "printer_name")
            if "MG3600" in printer_name:
                logging.info("Trying system lp command for Canon MG3600...")
                return self.print_with_lp_command(image_path, copies, printer_name)
            
            # Check printer status before printing
            if not self.check_printer_ready():
                logging.error("Printer is not ready for printing")
                return False
            
            # Validate image file exists and is readable
            if not os.path.exists(image_path):
                logging.error(f"Image file does not exist: {image_path}")
                return False
                
            # Check file size
            file_size = os.path.getsize(image_path)
            logging.info(f"Image file size: {file_size} bytes")
            
            printer_name = self.config.get("printing", "printer_name")
            printers = self.conn.getPrinters()
            
            # Use first available printer if configured printer not found
            if printer_name not in printers:
                if printers:
                    printer_name = list(printers.keys())[0]
                    logging.warning(f"Configured printer not found, using: {printer_name}")
                else:
                    logging.error("No printers available")
                    return False
            
            # Get paper size from config and convert to CUPS format
            paper_size = self.config.get("printing", "paper_size") or "A4"
            media_size = self.get_cups_media_size(paper_size)
            
            # # For Canon MG3600 series, default to A4 if 4x6 is configured
            # if "MG3600" in printer_name and paper_size == "4x6":
            #     logging.info("Canon MG3600 detected, using A4 instead of 4x6 for better compatibility")
            #     media_size = "iso_a4_210x297mm"
            
            # Print options - try minimal settings for Canon MG3600
            options = {
                'copies': str(copies)
            }
            
            # Try different approaches for Canon MG3600
            if "MG3600" in printer_name:
                # Try the most basic approach - just fit-to-page
                options.update({
                    'fit-to-page': 'true'  # Let printer handle sizing
                })
                logging.info("Using Canon MG3600 with fit-to-page option")
            
            
            # Log the print options for debugging
            logging.info(f"Printing to {printer_name} with options: {options}")
            logging.info(f"Image path: {image_path}")
            
            job_id = self.conn.printFile(printer_name, str(image_path), "PhotoBooth", options)
            logging.info(f"Print job {job_id} submitted for {copies} copies")
            
            # Monitor job progress for up to 30 seconds
            success = self.monitor_print_job(job_id, printer_name)
            
            return success
            
        except Exception as e:
            logging.error(f"Printing failed: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def monitor_print_job(self, job_id, printer_name, timeout=30):
        """Monitor print job progress and diagnose issues"""
        import time
        
        state_meanings = {
            3: "pending",
            4: "processing", 
            5: "processing-stopped",
            6: "canceled",
            7: "aborted",
            8: "completed",
            9: "completed"
        }
        
        start_time = time.time()
        last_state = None
        
        while time.time() - start_time < timeout:
            try:
                # Check job status
                job_attrs = self.conn.getJobAttributes(job_id)
                job_state = job_attrs.get('job-state', 'unknown')
                job_state_reasons = job_attrs.get('job-state-reasons', ['unknown'])
                state_meaning = state_meanings.get(job_state, f"unknown({job_state})")
                
                # Only log if state changed
                if job_state != last_state:
                    logging.info(f"Job {job_id} status: {job_state} ({state_meaning}), reasons: {job_state_reasons}")
                    last_state = job_state
                
                # Check if job completed successfully
                if job_state in [8, 9]:  # completed
                    logging.info(f"Print job {job_id} completed successfully!")
                    return True
                
                # Check if job failed
                if job_state in [5, 6, 7]:  # stopped, canceled, aborted
                    logging.error(f"Print job {job_id} failed - state: {job_state} ({state_meaning})")
                    logging.error(f"Job failure reasons: {job_state_reasons}")
                    
                    # Get detailed printer status
                    printers = self.conn.getPrinters()
                    if printer_name in printers:
                        printer_info = printers[printer_name]
                        printer_state = printer_info.get('printer-state', 'unknown')
                        printer_reasons = printer_info.get('printer-state-reasons', ['unknown'])
                        logging.error(f"Printer {printer_name} state: {printer_state}, reasons: {printer_reasons}")
                        
                        # Check for common issues
                        if 'media-needed' in printer_reasons:
                            logging.error("ISSUE: Printer needs paper - check if 4x6 paper is loaded")
                        if 'marker-supply-low' in printer_reasons:
                            logging.error("ISSUE: Low ink/toner")
                        if 'marker-supply-empty' in printer_reasons:
                            logging.error("ISSUE: Empty ink/toner cartridge")
                        if 'door-open' in printer_reasons:
                            logging.error("ISSUE: Printer door/cover is open")
                        if 'media-jam' in printer_reasons:
                            logging.error("ISSUE: Paper jam detected")
                    
                    return False
                
                # If job is stuck in pending for too long, diagnose
                if job_state == 3 and time.time() - start_time > 10:
                    if time.time() - start_time == 10:  # Log once after 10 seconds
                        logging.warning(f"Job {job_id} stuck in pending state - checking printer...")
                        
                        # Check printer queue
                        jobs = self.conn.getJobs(which_jobs='active')
                        logging.info(f"Active print jobs: {len(jobs)}")
                        for jid, job_info in jobs.items():
                            logging.info(f"Job {jid}: {job_info.get('job-name', 'unknown')}")
                        
                        # Check if printer is paused
                        printers = self.conn.getPrinters()
                        if printer_name in printers:
                            printer_info = printers[printer_name]
                            printer_state = printer_info.get('printer-state', 'unknown')
                            printer_reasons = printer_info.get('printer-state-reasons', ['unknown'])
                            logging.warning(f"Printer {printer_name} state: {printer_state}, reasons: {printer_reasons}")
                            
                            if printer_state == 5:  # stopped
                                logging.error("ISSUE: Printer is stopped/paused - check printer status")
                            if 'paused' in printer_reasons:
                                logging.error("ISSUE: Printer queue is paused")
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logging.error(f"Error monitoring job {job_id}: {e}")
                break
        
        logging.warning(f"Job {job_id} monitoring timed out after {timeout} seconds")
        return False
    
    def get_printer_media_sizes(self, printer_name=None):
        """Get supported media sizes from the printer PPD"""
        try:
            if not printer_name:
                printer_name = self.config.get("printing", "printer_name")
            
            ppd_path = self.conn.getPPD(printer_name)
            if ppd_path:
                logging.info(f"PPD file for {printer_name}: {ppd_path}")
                
                # Try to read PPD file to find supported media sizes
                try:
                    with open(ppd_path, 'r') as f:
                        ppd_content = f.read()
                    
                    # Look for PageSize options
                    media_sizes = []
                    lines = ppd_content.split('\n')
                    for line in lines:
                        if 'PageSize' in line and '4x6' in line.lower():
                            logging.info(f"Found 4x6 option: {line.strip()}")
                            media_sizes.append(line.strip())
                    
                    if media_sizes:
                        logging.info(f"Supported 4x6 media sizes: {media_sizes}")
                    else:
                        logging.info("No specific 4x6 media sizes found in PPD")
                        
                except Exception as e:
                    logging.error(f"Could not read PPD file: {e}")
            else:
                logging.warning(f"No PPD file found for {printer_name}")
                
        except Exception as e:
            logging.error(f"Error getting printer media sizes: {e}")
    
    def clear_print_queue(self, printer_name=None):
        """Clear all pending print jobs for the printer"""
        try:
            if not printer_name:
                printer_name = self.config.get("printing", "printer_name")
            
            # Get all jobs for this printer
            jobs = self.conn.getJobs(which_jobs='not-completed', my_jobs=False)
            cleared_jobs = []
            
            for job_id, job_info in jobs.items():
                job_printer = job_info.get('printer-name', '')
                if job_printer == printer_name:
                    try:
                        self.conn.cancelJob(job_id)
                        cleared_jobs.append(job_id)
                        logging.info(f"Canceled stuck job {job_id}")
                    except Exception as e:
                        logging.error(f"Failed to cancel job {job_id}: {e}")
            
            if cleared_jobs:
                logging.info(f"Cleared {len(cleared_jobs)} stuck print jobs")
                return True
            else:
                logging.info("No stuck print jobs found")
                return False
                
        except Exception as e:
            logging.error(f"Error clearing print queue: {e}")
            return False
    
    def print_with_lp_command(self, image_path, copies, printer_name):
        """Try printing using system lp command instead of Python CUPS"""
        try:
            import subprocess
            
            # Build lp command with correct Canon MG3600 options
            cmd = [
                'lp',
                '-d', printer_name,  # destination printer
                '-n', str(copies),   # number of copies
                '-o', 'PageSize=4x6.Borderless',  # Use the default borderless 4x6
                '-o', 'MediaType=Photographic',   # Use photo paper type
                '-o', 'InputSlot=Main',            # Use main paper tray
                '-o', 'print-scaling=fit',         # Fit to page
                str(image_path)
            ]
            
            logging.info(f"Executing lp command: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logging.info(f"lp command succeeded: {result.stdout.strip()}")
                # Extract job ID from output (German: "Anfrage-ID ist Canon_MG3600_series-XX")
                output = result.stdout.strip()
                job_id = None
                
                # Try both English and German formats
                if "request id is" in output.lower():
                    job_id_str = output.split("request id is")[-1].strip()
                elif "anfrage-id ist" in output.lower():
                    job_id_str = output.split("anfrage-id ist")[-1].strip()
                else:
                    job_id_str = output
                
                # Extract numeric job ID
                if '-' in job_id_str:
                    job_id = job_id_str.split('-')[-1].split()[0]  # Get first part after split by space
                    if job_id.isdigit():
                        logging.info(f"Monitoring lp job {job_id}...")
                        return self.monitor_print_job(int(job_id), printer_name)
                
                # If we can't extract job ID, just return success
                logging.info("Job submitted successfully, but couldn't extract job ID for monitoring")
                return True
            else:
                logging.error(f"lp command failed: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("lp command timed out")
            return False
        except Exception as e:
            logging.error(f"Error with lp command: {e}")
            return False
    
    def clear_specific_job(self, job_id):
        """Clear a specific job by ID"""
        try:
            if not self.conn:
                return False
            
            self.conn.cancelJob(job_id)
            logging.info(f"Cancelled specific job {job_id}")
            return True
        except Exception as e:
            logging.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    def get_cups_media_size(self, paper_size):
        """Convert paper size to CUPS media format"""
        size_map = {
            "A4": "iso_a4_210x297mm",
            "4x6": "na_index-4x6_4x6in",
            "Letter": "na_letter_8.5x11in",
            "Legal": "na_legal_8.5x14in"
        }
        return size_map.get(paper_size, "iso_a4_210x297mm")
    
    def check_printer_ready(self):
        """Check if printer is ready to accept jobs"""
        try:
            printer_name = self.config.get("printing", "printer_name")
            printers = self.conn.getPrinters()
            
            if printer_name not in printers:
                logging.error(f"Printer {printer_name} not found")
                return False
            
            printer_info = printers[printer_name]
            printer_state = printer_info.get('printer-state', 0)
            printer_reasons = printer_info.get('printer-state-reasons', [])
            
            # Log printer status
            state_meanings = {3: "idle", 4: "printing", 5: "stopped"}
            state_meaning = state_meanings.get(printer_state, f"unknown({printer_state})")
            logging.info(f"Printer {printer_name} state: {printer_state} ({state_meaning})")
            logging.info(f"Printer reasons: {printer_reasons}")
            
            # Check if printer is in a good state (idle or printing)
            if printer_state in [3, 4]:  # idle or printing
                return True
            else:
                logging.warning(f"Printer {printer_name} not ready - state: {printer_state}, reasons: {printer_reasons}")
                return False
                
        except Exception as e:
            logging.error(f"Error checking printer status: {e}")
            return False
    
    def get_printer_status(self):
        try:
            if self.conn:
                printers = self.conn.getPrinters()
                return len(printers) > 0
        except:
            pass
        return False
    
    def get_printer_capabilities(self, printer_name=None):
        """Get printer capabilities for debugging"""
        try:
            if not self.conn:
                return None
            
            if not printer_name:
                printer_name = self.config.get("printing", "printer_name")
            
            printers = self.conn.getPrinters()
            if printer_name in printers:
                printer_info = printers[printer_name]
                logging.info(f"Printer {printer_name} info: {printer_info}")
                
                # Get PPD attributes
                ppd = self.conn.getPPD(printer_name)
                if ppd:
                    logging.info(f"PPD file for {printer_name}: {ppd}")
                
                return printer_info
        except Exception as e:
            logging.error(f"Error getting printer capabilities: {e}")
        return None

class FileManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.setup_directories()
    
    def setup_directories(self):
        try:
            # Create all necessary directories
            paths = [
                self.config.get("storage", "originals_path"),
                self.config.get("storage", "framed_path"),
                self.config.get("storage", "sync_path") + "/originals",
                self.config.get("storage", "sync_path") + "/framed",
                "./logs"
            ]
            
            for path in paths:
                Path(path).mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            logging.error(f"Directory setup failed: {e}")
    
    def cleanup_old_files(self):
        try:
            max_photos = self.config.get("storage", "max_local_photos")
            
            for folder in ["originals_path", "framed_path"]:
                path = Path(self.config.get("storage", folder))
                if path.exists():
                    files = sorted(path.glob("*.jpg"), key=lambda x: x.stat().st_mtime)
                    if len(files) > max_photos:
                        for file in files[:-max_photos]:
                            file.unlink()
                            logging.info(f"Cleaned up old file: {file}")
        except Exception as e:
            logging.error(f"Cleanup failed: {e}")

class PhotoBoothApp:
    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        # Setup logging after config is loaded
        self.config_manager.setup_logging()
        self.camera_manager = CameraManager(self.config_manager)
        self.image_processor = ImageProcessor(self.config_manager)
        self.print_manager = PrintManager(self.config_manager)
        self.file_manager = FileManager(self.config_manager)
        
        self.current_photo = None
        self.current_photo_path = None
        self.countdown_active = False
        self.selected_frame = None
        
        self.setup_ui()
        self.start_camera_preview()
        
    def setup_ui(self):
        # Configure main window
        self.root.title("Photo Booth")
        self.root.configure(bg='black')
        
        if self.config_manager.get("ui", "fullscreen"):
            self.root.attributes('-fullscreen', True)
            self.root.bind('<Escape>', lambda e: self.root.quit())
        else:
            self.root.geometry("1920x1080")
        
        # Create main frame
        self.main_frame = tk.Frame(self.root, bg='black')
        self.main_frame.pack(fill='both', expand=True)
        
        # Camera preview label
        self.camera_label = tk.Label(self.main_frame, bg='black')
        self.camera_label.pack(fill='both', expand=True)
        
        # Overlay frame for buttons
        self.overlay_frame = tk.Frame(self.main_frame, bg='black')
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Create button image for overlay
        try:
            self.button_image = self.create_button_image("TAKE PHOTO", 220)
        except Exception as e:
            logging.error(f"Failed to create button image: {e}")
            self.button_image = None
        
        # Bind click event to camera label for button interaction
        self.camera_label.bind('<Button-1>', self.on_camera_click)
        self.camera_label.configure(cursor='hand2')  # Show it's clickable
        
        # Initialize button as visible (countdown_image starts as None)
        
        # Settings button (transparent style)
        settings_image = self.create_settings_button_image()
        settings_photo = ImageTk.PhotoImage(settings_image)
        
        self.settings_button = tk.Label(
            self.main_frame,
            image=settings_photo,
            bg='black',
            cursor='hand2'
        )
        self.settings_button.image = settings_photo  # Keep reference
        self.settings_button.bind('<Button-1>', lambda e: self.show_settings())
        self.settings_button.place(x=20, y=20)
        
        # Status frame
        self.status_frame = tk.Frame(self.main_frame, bg='black')
        self.status_frame.place(relx=1.0, rely=0.0, anchor='ne', x=-20, y=20)
        
        # Printer status
        self.printer_status = tk.Label(
            self.status_frame,
            text="🖨️ Ready" if self.print_manager.get_printer_status() else "🖨️ Offline",
            font=('Arial', 16),
            bg='black',
            fg='green' if self.print_manager.get_printer_status() else 'red'
        )
        self.printer_status.pack()
        
        # Variables for countdown overlay
        self.countdown_number = None
        self.countdown_image = None
        
        # Variables for button overlay
        self.button_image = None
        self.button_position = None
        
        # Initial state set
        
        # Create hidden frames for different screens
        self.create_photo_review_screen()
        self.create_settings_screen()
        
    def create_photo_review_screen(self):
        self.review_frame = tk.Frame(self.root, bg='black')
        
        # Photo display
        self.review_photo_label = tk.Label(self.review_frame, bg='black')
        self.review_photo_label.pack(pady=20)
        
        # Button frame
        button_frame = tk.Frame(self.review_frame, bg='black')
        button_frame.pack(pady=20)
        
        # Retake button
        tk.Button(
            button_frame,
            text="🔄 RETAKE",
            font=('Arial', 20, 'bold'),
            bg='orange',
            fg='white',
            width=12,
            height=2,
            command=self.retake_photo
        ).pack(side='left', padx=10)
        
        # Print button
        tk.Button(
            button_frame,
            text="🖨️ PRINT",
            font=('Arial', 20, 'bold'),
            bg='green',
            fg='white',
            width=12,
            height=2,
            command=self.show_print_options
        ).pack(side='left', padx=10)
        
        # Save & Continue button
        tk.Button(
            button_frame,
            text="✅ SAVE",
            font=('Arial', 20, 'bold'),
            bg='blue',
            fg='white',
            width=12,
            height=2,
            command=self.save_and_continue
        ).pack(side='left', padx=10)
        
    def create_settings_screen(self):
        self.settings_frame = tk.Frame(self.root, bg='white')
        
        # Title
        tk.Label(
            self.settings_frame,
            text="Settings",
            font=('Arial', 32, 'bold'),
            bg='white'
        ).pack(pady=20)
        
        # Frame selection
        frame_label = tk.Label(
            self.settings_frame,
            text="Select Frame:",
            font=('Arial', 18),
            bg='white'
        )
        frame_label.pack(pady=10)
        
        # Frame selection buttons
        frame_button_frame = tk.Frame(self.settings_frame, bg='white')
        frame_button_frame.pack(pady=10)
        
        # Load available frames
        self.load_frame_options(frame_button_frame)
        
        # Printer maintenance section
        maintenance_label = tk.Label(
            self.settings_frame,
            text="Printer Maintenance:",
            font=('Arial', 18),
            bg='white'
        )
        maintenance_label.pack(pady=(20, 10))
        
        # Clear print queue button
        clear_queue_btn = tk.Button(
            self.settings_frame,
            text="Clear Print Queue",
            font=('Arial', 14, 'bold'),
            bg='orange',
            fg='white',
            width=20,
            height=2,
            command=self.clear_printer_queue
        )
        clear_queue_btn.pack(pady=5)
        
        # Back button
        tk.Button(
            self.settings_frame,
            text="← BACK",
            font=('Arial', 20, 'bold'),
            bg='gray',
            fg='white',
            width=12,
            height=2,
            command=self.show_main_screen
        ).pack(pady=20)
        
    def load_frame_options(self, parent):
        frames_path = Path(self.config_manager.get("frames", "frames_path"))
        
        # No frame option
        tk.Button(
            parent,
            text="No Frame",
            font=('Arial', 14),
            bg='lightgray',
            width=15,
            height=2,
            command=lambda: self.select_frame(None)
        ).pack(side='left', padx=5)
        
        # Load frame files
        if frames_path.exists():
            for frame_file in frames_path.glob("*.png"):
                frame_name = frame_file.stem.replace('_', ' ').title()
                tk.Button(
                    parent,
                    text=frame_name,
                    font=('Arial', 14),
                    bg='lightblue',
                    width=15,
                    height=2,
                    command=lambda f=frame_file.name: self.select_frame(f)
                ).pack(side='left', padx=5)
    
    def select_frame(self, frame_file):
        self.selected_frame = frame_file
        logging.info(f"Selected frame: {frame_file}")
    
    def create_countdown_image(self, number):
        """Create a circular countdown image with transparent background"""
        # Create a large image for the circle
        size = 300
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        # Draw semi-transparent circle
        circle_color = (30, 100, 200, 150)  # Blueish with transparency
        circle_outline = (255, 255, 255, 200)  # White outline
        margin = 20
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=circle_color, outline=circle_outline, width=8)
        
        # Add the number in the center
        try:
            # Try to use a better font if available
            font = ImageFont.truetype("Arial", 120)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Get text dimensions for centering
        text = str(number)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw text with shadow for better visibility
        shadow_offset = 3
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return image
    
    def create_smile_overlay(self):
        """Create a 'SMILE!' overlay with circular background"""
        size = 300
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        # Draw semi-transparent circle (different color for smile)
        circle_color = (0, 150, 0, 180)  # Green with transparency
        circle_outline = (255, 255, 255, 255)  # White outline
        margin = 20
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=circle_color, outline=circle_outline, width=8)
        
        # Add "SMILE!" text
        try:
            font = ImageFont.truetype("Arial", 60)
        except:
            font = ImageFont.load_default()
        
        text = "SMILE!"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw text with shadow
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return image
    
    def create_button_image(self, text, size=200):
        """Create a circular button image with transparent background"""
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        # Draw semi-transparent circle (same style as countdown)
        circle_color = (30, 100, 200, 150)  # Blueish with transparency
        circle_outline = (255, 255, 255, 200)  # White outline
        margin = 10
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=circle_color, outline=circle_outline, width=6)
        
        # Add the text
        try:
            font = ImageFont.truetype("Arial", 28)  # Increased font size
        except Exception as e:
            logging.warning(f"Could not load Arial font, using default: {e}")
            try:
                font = ImageFont.load_default()
            except Exception as e2:
                logging.error(f"Could not load default font: {e2}")
                font = None
        
        # Get text dimensions for centering
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            # Fallback dimensions if no font
            text_width = len(text) * 12
            text_height = 20
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw text with shadow
        shadow_offset = 2
        if font:
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 200))
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        else:
            # Fallback without font
            draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 200))
            draw.text((x, y), text, fill=(255, 255, 255, 255))
        
        return image
    
    def create_settings_button_image(self, size=100):
        """Create a settings text with transparent background"""
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        # Just draw the settings text without background
        try:
            font = ImageFont.truetype("Arial", 16)
        except Exception as e:
            try:
                font = ImageFont.load_default()
            except Exception as e2:
                font = None
        
        # Center the settings text
        text = "Settings"
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = 60  # Longer text needs more width
            text_height = 20
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw gear icon with shadow for visibility
        shadow_offset = 1
        if font:
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 150))
            draw.text((x, y), text, font=font, fill=(200, 200, 200, 255))
        else:
            draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 150))
            draw.text((x, y), text, fill=(200, 200, 200, 255))
        
        return image
        
    def on_camera_click(self, event):
        """Handle clicks on the camera preview to detect button clicks"""
        if hasattr(self, 'button_image_position') and self.button_image_position is not None and self.countdown_image is None:
            # Get the actual label size
            label_width = self.camera_label.winfo_width()
            label_height = self.camera_label.winfo_height()
            
            # Get the image size that was displayed
            if hasattr(self, 'current_image_size') and self.current_image_size:
                image_width, image_height = self.current_image_size
                
                # Calculate scaling and offset for the image within the label
                # The image is centered in the label, so calculate the offset
                x_offset = (label_width - image_width) // 2
                y_offset = (label_height - image_height) // 2
                
                # Convert click coordinates from label space to image space
                image_click_x = event.x - x_offset
                image_click_y = event.y - y_offset
                
                # Get button bounds in image coordinates
                x1, y1, x2, y2 = self.button_image_position
                
                # Check if click is within button bounds in image coordinates
                if x1 <= image_click_x <= x2 and y1 <= image_click_y <= y2:
                    self.start_countdown()
        
    def start_camera_preview(self):
        self.camera_manager.start_preview()
        self.update_camera_preview()
        
    def update_camera_preview(self):
        if self.camera_manager.preview_running:
            frame = self.camera_manager.get_frame()
            if frame is not None:
                # Convert to RGB and resize for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                
                # Resize to fit screen
                display_size = (1280, 720)
                pil_image.thumbnail(display_size, Image.Resampling.LANCZOS)
                
                # Create a copy for overlays
                display_image = pil_image.copy()
                
                # If countdown is active, overlay the countdown
                if self.countdown_image is not None:
                    # Calculate position to center the countdown overlay
                    overlay_size = self.countdown_image.size
                    image_size = display_image.size
                    
                    x = (image_size[0] - overlay_size[0]) // 2
                    y = (image_size[1] - overlay_size[1]) // 2
                    
                    # Paste the countdown overlay with transparency
                    display_image.paste(self.countdown_image, (x, y), self.countdown_image)
                
                                # If button should be shown, overlay the button
                # Ensure button image exists
                if not hasattr(self, 'button_image') or self.button_image is None:
                    self.button_image = self.create_button_image("TAKE PHOTO", 220)
                    
                button_should_show = (self.button_image is not None and 
                                    self.countdown_image is None)
                
                if button_should_show:
                    # Calculate position to center the button overlay
                    button_size = self.button_image.size
                    image_size = display_image.size
                    
                    x = (image_size[0] - button_size[0]) // 2
                    y = (image_size[1] - button_size[1]) // 2
                    
                    # Store both image coordinates and widget coordinates for click detection
                    self.button_image_position = (x, y, x + button_size[0], y + button_size[1])
                    self.current_image_size = image_size
                    
                    # Paste the button overlay with transparency
                    display_image.paste(self.button_image, (x, y), self.button_image)
                    
 
                else:
                    # Clear button position when not showing
                    self.button_image_position = None
                    self.current_image_size = None
                    

                
                pil_image = display_image
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(pil_image)
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo
                
        # Schedule next update
        self.root.after(33, self.update_camera_preview)  # ~30 FPS
        
    def start_countdown(self):
        if self.countdown_active:
            return
            
        self.countdown_active = True
        # Button will be hidden automatically when countdown starts (countdown_image is not None)
        
        countdown_time = self.config_manager.get("ui", "countdown_time")
        
        def countdown(count):
            if count > 0:
                # Set countdown image for overlay
                self.countdown_image = self.create_countdown_image(count)
                self.root.after(1000, lambda: countdown(count - 1))
            else:
                # Show "SMILE!" message briefly
                self.countdown_image = self.create_smile_overlay()
                
                # Take the photo after a brief delay
                self.root.after(800, self.capture_photo)
        
        countdown(countdown_time)
        
    def capture_photo(self):
        try:
            # Clear countdown overlay
            self.countdown_image = None
            
            # Capture the photo
            cv_image = self.camera_manager.capture_photo()
            
            if cv_image is not None:
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"photo_{timestamp}.jpg"
                
                # Save original
                original_path = self.image_processor.save_original(cv_image, filename)
                
                # Apply frame and save
                framed_path, pil_image = self.image_processor.apply_frame_and_save(
                    cv_image, f"framed_{filename}", self.selected_frame
                )
                
                self.current_photo = pil_image if pil_image else Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
                self.current_photo_path = framed_path if framed_path else original_path
                
                # Show photo review
                self.show_photo_review()
                
                logging.info(f"Photo captured: {filename}")
            else:
                messagebox.showerror("Error", "Failed to capture photo!")
                self.reset_capture_button()
                
        except Exception as e:
            logging.error(f"Photo capture error: {e}")
            messagebox.showerror("Error", f"Photo capture failed: {str(e)}")
            self.reset_capture_button()
        
        self.countdown_active = False
        
    def show_photo_review(self):
        # Hide main screen
        self.main_frame.pack_forget()
        
        # Display captured photo
        if self.current_photo:
            # Resize for display
            display_photo = self.current_photo.copy()
            display_photo.thumbnail((800, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(display_photo)
            
            self.review_photo_label.configure(image=photo)
            self.review_photo_label.image = photo
        
        # Show review screen
        self.review_frame.pack(fill='both', expand=True)
        
    def retake_photo(self):
        self.show_main_screen()
        
    def show_print_options(self):
        if not self.current_photo_path:
            messagebox.showerror("Error", "No photo to print!")
            return
            
        # Create custom print dialog (better for Raspberry Pi)
        copies = self.create_print_dialog()
        
        if copies and copies > 0:
            # SIMPLIFIED APPROACH: Try printing the original image directly first
            # Bypass complex image processing that might be causing issues
            logging.info("Attempting to print original image directly (bypassing complex processing)")
            
            # Send original to printer directly
            if self.print_manager.print_image(self.current_photo_path, copies):
                messagebox.showinfo("Success", f"Printing {copies} copies!")
            else:
                messagebox.showerror("Error", "Printing failed!")
    
    def create_print_dialog(self):
        """Create a custom print dialog that works better on Raspberry Pi"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Print Copies")
        dialog.geometry("400x200")
        dialog.configure(bg='white')
        dialog.resizable(False, False)
        
        # Center the dialog on screen
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Store result
        result = None
        
        # Title label
        title_label = tk.Label(
            dialog,
            text="How many copies would you like?",
            font=('Arial', 16, 'bold'),
            bg='white'
        )
        title_label.pack(pady=20)
        
        # Copies frame
        copies_frame = tk.Frame(dialog, bg='white')
        copies_frame.pack(pady=10)
        
        # Number buttons (1-5)
        max_copies = self.config_manager.get("printing", "max_copies")
        for i in range(1, min(max_copies + 1, 6)):  # Max 5 buttons
            btn = tk.Button(
                copies_frame,
                text=str(i),
                font=('Arial', 20, 'bold'),
                width=3,
                height=2,
                bg='lightblue',
                fg='black',
                command=lambda x=i: self.set_dialog_result(dialog, x)
            )
            btn.pack(side='left', padx=5)
        
        # Button frame
        button_frame = tk.Frame(dialog, bg='white')
        button_frame.pack(pady=20)
        
        # Cancel button
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            font=('Arial', 14, 'bold'),
            width=10,
            height=2,
            bg='gray',
            fg='white',
            command=lambda: self.set_dialog_result(dialog, None)
        )
        cancel_btn.pack(side='left', padx=10)
        
        # Wait for user interaction
        dialog.wait_window()
        
        return getattr(dialog, 'result', None)
    
    def set_dialog_result(self, dialog, value):
        """Set the result and close the dialog"""
        dialog.result = value
        dialog.destroy()
    
    def save_and_continue(self):
        # Cleanup old files
        self.file_manager.cleanup_old_files()
        
        messagebox.showinfo("Saved", "Photo saved successfully!")
        self.show_main_screen()
        
    def clear_printer_queue(self):
        """Clear print queue and show result"""
        try:
            success = self.print_manager.clear_print_queue()
            if success:
                messagebox.showinfo("Success", "Print queue cleared successfully!")
            else:
                messagebox.showinfo("Info", "No stuck print jobs found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear print queue: {e}")
    
    def show_settings(self):
        self.main_frame.pack_forget()
        self.settings_frame.pack(fill='both', expand=True)
        
    def show_main_screen(self):
        # Hide other screens
        self.review_frame.pack_forget()
        self.settings_frame.pack_forget()
        
        # Reset capture button
        self.reset_capture_button()
        
        # Show main screen
        self.main_frame.pack(fill='both', expand=True)
        
    def reset_capture_button(self):
        # Clear countdown overlay if visible
        self.countdown_image = None
        self.countdown_active = False
        
        # Button will be shown automatically when countdown_image is None and countdown_active is False
        
    def run(self):
        try:
            logging.info("Photo Booth application started")
            self.root.mainloop()
        except KeyboardInterrupt:
            logging.info("Application interrupted by user")
        finally:
            self.cleanup()
            
    def cleanup(self):
        logging.info("Cleaning up resources...")
        self.camera_manager.stop_preview()
        self.camera_manager.release()

def main():
    app = PhotoBoothApp()
    app.run()

if __name__ == "__main__":
    main()