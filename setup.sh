# setup.sh - Photo Booth Installation Script
#!/bin/bash

echo "Photo Booth Setup Script"
echo "========================"

# Create directory structure
echo "Creating directory structure..."
mkdir -p /home/pi/photobooth/{app,assets/frames,captured_photos/{originals,framed,thumbnails},google_drive_sync/{originals,framed},config,logs}

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-dev python3-opencv python3-pil python3-tk
sudo apt install -y cups cups-client python3-cups
sudo apt install -y v4l-utils

# Install Python packages
echo "Installing Python packages..."
pip3 install opencv-python pillow pycups pathlib-ng

# Set up camera permissions
echo "Setting up camera permissions..."
sudo usermod -a -G video pi

# Set up printer permissions
echo "Setting up printer permissions..."
sudo usermod -a -G lpadmin pi

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/photobooth.service > /dev/null <<EOF
[Unit]
Description=Photo Booth Application
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
WorkingDirectory=/home/pi/photobooth
ExecStart=/usr/bin/python3 /home/pi/photobooth/app/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
EOF

# Create sample frame files
echo "Creating sample frames..."
python3 << 'EOF'
from PIL import Image, ImageDraw
import os

# Create frames directory
frames_dir = "/home/pi/photobooth/assets/frames"
os.makedirs(frames_dir, exist_ok=True)

# Create a simple classic frame
def create_classic_frame():
    # Create 1200x1800 frame (4:6 ratio)
    width, height = 1200, 1800
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    # Create border
    border_width = 50
    outer_color = (139, 69, 19, 255)  # Brown
    inner_color = (222, 184, 135, 255)  # Beige
    
    # Outer border
    draw.rectangle([0, 0, width-1, height-1], fill=outer_color)
    # Inner border  
    draw.rectangle([border_width, border_width, width-border_width-1, height-border_width-