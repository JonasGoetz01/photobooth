# PhotoBooth Application

A Python-based photo booth application with configurable settings for different environments.

## Features

- Camera preview and photo capture
- Photo framing with custom frames
- Printing support via CUPS
- Configurable storage locations
- Countdown timer for photos
- Review and retake functionality

## Setup

### Prerequisites

- Python 3.7+
- Webcam/camera
- Optional: CUPS-compatible printer

### Installation

1. **Clone/download the project**
2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### macOS Setup

On macOS, you may need to install additional system dependencies:

```bash
# Install Python with Tkinter support
brew install python-tk

# For CUPS printing support (optional)
brew install cups
```

## Configuration

The application uses a JSON configuration file located at `config/settings.json`. This file is automatically created with default settings on first run.

### Configuration Sections

#### Camera Settings
```json
"camera": {
    "resolution": [1920, 1080],        // Capture resolution
    "preview_resolution": [1280, 720], // Preview resolution
    "fps": 30,                         // Frames per second
    "device_id": 0                     // Camera device ID
}
```

#### UI Settings
```json
"ui": {
    "fullscreen": false,    // Run in fullscreen mode
    "button_size": "large", // Button size
    "theme": "dark",        // UI theme
    "countdown_time": 3     // Countdown seconds before capture
}
```

#### Storage Settings
```json
"storage": {
    "max_local_photos": 100,                        // Max photos to keep locally
    "auto_sync": true,                              // Enable auto-sync
    "originals_path": "./captured_photos/originals", // Original photos path
    "framed_path": "./captured_photos/framed",       // Framed photos path
    "sync_path": "./google_drive_sync"               // Sync folder path
}
```

#### Frame Settings
```json
"frames": {
    "default_frame": "classic_frame.png", // Default frame file
    "frames_path": "./assets/frames"      // Frames directory
}
```

#### Printing Settings
```json
"printing": {
    "default_copies": 1,      // Default number of copies
    "max_copies": 5,          // Maximum copies allowed
    "quality": "high",        // Print quality
    "paper_size": "4x6",      // Paper size
    "printer_name": "Canon_Printer" // Printer name
}
```

#### Logging Settings
```json
"logs": {
    "log_path": "./logs/photobooth.log" // Log file location
}
```

## Usage

### Running the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python main.py
```

### Controls

- **Take Photo**: Click the main capture button or press it during countdown
- **Settings**: Click the gear icon to access frame selection
- **Review Screen**: After taking a photo, you can:
  - **Retake**: Take another photo
  - **Print**: Send to printer (with copy selection)
  - **Save**: Save and continue

### Adding Custom Frames

1. Create PNG image files with transparent centers
2. Place them in the `assets/frames/` directory
3. Frames will appear in the settings screen

## Platform Differences

### Raspberry Pi Configuration
For Raspberry Pi deployment, update the config paths:
```json
{
    "storage": {
        "originals_path": "/home/pi/photobooth/captured_photos/originals",
        "framed_path": "/home/pi/photobooth/captured_photos/framed",
        "sync_path": "/home/pi/photobooth/google_drive_sync"
    },
    "logs": {
        "log_path": "/home/pi/photobooth/logs/photobooth.log"
    }
}
```

### macOS Configuration (Default)
The default configuration uses relative paths suitable for development and testing:
```json
{
    "storage": {
        "originals_path": "./captured_photos/originals",
        "framed_path": "./captured_photos/framed",
        "sync_path": "./google_drive_sync"
    },
    "logs": {
        "log_path": "./logs/photobooth.log"
    }
}
```

## Troubleshooting

### Common Issues

1. **Camera not detected**: Check `device_id` in config, try different values (0, 1, 2...)
2. **Tkinter not found**: Install `python-tk` package
3. **Permission errors**: Ensure write permissions for photo and log directories
4. **Printer not working**: Check CUPS configuration and printer name in config

### Logs

Check the log file (default: `./logs/photobooth.log`) for detailed error messages and debugging information. 