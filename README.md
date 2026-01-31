# AgriGuard — Automated Animal Detection and Deterrent System

An AI-powered animal detection and deterrent system to reduce manual farmland monitoring and prevent crop damage. AgriGuard uses edge-friendly object detection to identify animals approaching farmland and triggers configurable deterrents (audio, visual, or mechanical) while logging events for farmers.

Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Training / Improving Detection](#training--improving-detection)
- [Deployment Considerations](#deployment-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)

## Overview
AgriGuard is designed for small-to-medium farms to detect animals (wildlife or domestic) near fields using a camera and AI-based object detection running at the edge. When an animal is detected, the system can:
- Trigger audio playback (scare sounds),
- Activate lights/strobes,
- Sound an alarm,
- Send a notification or log the event for later review.

The project is organized to run on low-power systems such as a Raspberry Pi, and can be adapted for microcontrollers or edge accelerators (Coral, NPU).

## Key Features
- Real-time animal detection using a lightweight object detection model.
- Configurable deterrent actions (audio, light, GPIO-controlled devices).
- Local logging of events with timestamped snapshots.
- Extensible — support for different models and notification channels.
- Pipenv-based dependency management (Pipfile included).

## System Architecture
- Camera capture module -> Object detection model -> Decision / action module -> Deterrent hardware (speaker, LED, relay) and logging/notification.
- Optional: Web UI or remote notification to view live feed, recent detections, and system health.

A recommended simple flow:
1. Capture frame from camera.
2. Run detection model on the frame.
3. If detection confidence > threshold and matched class is configured:
   - Save snapshot
   - Log event
   - Trigger deterrent (play sound / toggle GPIO)
   - Optionally send notification (SMS/email/HTTP webhook)

## Hardware Requirements (example)
Minimum configuration (adjust based on performance needs):
- Raspberry Pi 3/4 (4GB recommended) or equivalent SBC
- Camera (Raspberry Pi Camera Module or USB webcam)
- Speaker (3.5mm or USB) or piezo buzzer
- Relay or driver module for lights / other actuators (optional)
- Power supply and enclosure suitable for outdoor use
- Optional: Coral USB Accelerator / NPU for better performance

## Software Requirements
- Python 3.8+ (tested), compatible with 3.7+
- Pipenv (Pipfile provided) OR python venv + pip
- OpenCV (cv2)
- A deep learning runtime: PyTorch OR TensorFlow, or a TFLite runtime for edge models
- Optional libraries: RPi.GPIO (for Raspberry Pi GPIO control), paho-mqtt, requests

Note: The exact model runtime depends on the model you choose (YOLO, MobileNet-SSD, TensorFlow Lite, etc.). Use an edge-friendly model for Raspberry Pi.

## Installation

Clone the repo:
```bash
git clone https://github.com/omkaryadav18/AgriGuard---Automated-Animal-Detection-and-Deterrent-System.git
cd AgriGuard---Automated-Animal-Detection-and-Deterrent-System
```

Using Pipenv (recommended since a Pipfile is included):
```bash
pip install pipenv
pipenv install --dev
pipenv shell
```

If you prefer venv + requirements:
- If a `requirements.txt` is added later:
```bash
python3 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

Place model weights (example):
- Create a `models/` directory and put your detection weights there (e.g., `models/detect.pt` or `models/detect.tflite`).
- Update `config.json` or the configuration file (see [Configuration](#configuration)) to point to the model.

Note: The repository contains an `AgriGuardplus/` directory — check it for project entry points, example scripts, and hardware integration code. Adjust the commands below to match the actual entry script if present.

## Configuration
Create or edit a configuration file (e.g., `config.json`) with these typical settings:
- camera:
  - device index or URL (e.g., `0` or `rtsp://...`)
  - frame width, height, fps
- model:
  - type (e.g., `yolov11`, `tflite`)
  - path to model weights
  - confidence threshold (e.g., 0.5)
  - classes to detect (e.g., `["cow","deer","boar"]`)
- deterrent:
  - audio file path
  - GPIO pin mapping
  - cooldown / debounce time (to avoid repeated triggers)
- logging:
  - disk path for snapshots
  - retention policy
- notifications:
  - webhook URL / SMTP / MQTT settings

Example config snippet:
```json
{
  "camera": {"device": 0, "width": 640, "height": 480},
  "model": {"type": "tflite", "path": "models/detect.tflite", "confidence": 0.5},
  "deterrent": {"audio": "assets/siren.wav", "gpio_pin": 17, "cooldown_seconds": 30},
  "logging": {"snapshots_dir": "logs/snapshots"}
}
```

## Running the System

General steps (adapt to actual entrypoint script inside the repo):
1. Activate your environment:
   - With Pipenv: `pipenv shell`
   - With venv: `source venv/bin/activate`
2. Ensure your model and config are in place.
3. Start the detection service (replace `src/main.py` with the actual script path):
```bash
python src/main.py --config config.json
```

If you prefer to test with a single-image detection script, run:
```bash
python scripts/detect_image.py --image test.jpg --model models/detect.tflite
```

Notes:
- If the repository contains specific entrypoint scripts in `AgriGuardplus/`, open and run those as instructed inside the files.
- For headless Raspberry Pi, disable X-windows display output and run the script in terminal or as a systemd service.

## Training / Improving Detection
- Collect images of target animals from your area (day/night, different distances/angles).
- Label images in a supported format (e.g., COCO, Pascal VOC, YOLO).
- Fine-tune a pretrained lightweight detection model (MobileNet-SSD, YOLOv5n/YOLOv8n) for better accuracy on local species.
- Convert trained weights to a runtime suitable for deployment (PyTorch -> TorchScript, TensorFlow -> TFLite, or use ONNX for accelerators).

Example training workflow:
1. Prepare dataset and labels.
2. Use your chosen framework's training script to fine-tune.
3. Export model and test locally before deploying to edge device.

## Deployment Considerations
- For Raspberry Pi: prefer TensorFlow Lite or a quantized PyTorch model (or use Coral USB Accelerator).
- Use USB/RTSP cameras with stable mounts and protective enclosures.
- Add a UPS or battery solution for power stability.
- To run as a service:
  - Create a systemd unit to start the detection service at boot.
  - Or use Docker (if available on the hardware) and mount devices properly.

## Troubleshooting
- Low FPS:
  - Reduce frame size, lower model complexity (use smaller model), or use hardware acceleration.
- False positives:
  - Increase confidence threshold, collect more labeled negative samples, or use motion-filtering (trigger only if movement is detected).
- GPIO not triggering:
  - Verify wiring, confirm the GPIO library is installed and that the script is run with required permissions (or sudo as needed).
- Camera not found:
  - Confirm camera index, test with `ffmpeg` or `v4l2-ctl`, ensure camera accessible to user.

## Contributing
Contributions are welcome! Suggested workflow:
1. Fork the repo.
2. Create a feature branch: `git checkout -b feat/your-feature`.
3. Add tests and update documentation.
4. Open a pull request describing your changes.

Please open issues for bugs, feature requests, or help with hardware integration.


## Acknowledgements
- Open-source object detection frameworks and model zoos (YOLO, TensorFlow, PyTorch).
- Hardware and community projects demonstrating edge AI for agriculture.

## Contact
Maintainer: omkaryadav18 (GitHub)
For questions, feature requests, or help with deployment, please open an issue or reach out via your GitHub profile.
