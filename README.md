# Array ADB  
Adaptive LED Matrix High Beam (ADB) Research Platform  
for Samsung PixCell LED

Experimental adaptive driving beam system combining:
PixCell LED control · OEM automotive optics · Vision-assisted logic

⚠️ Research & evaluation only. Not street-legal.


```
┌─────────────────┐     UART 500000     ┌─────────────────┐     ESP-NOW     ┌─────────────────┐
│   视觉识别模块   │ ──────────────────► │     ESP32       │ ──────────────► │   透镜模块      │
│   (YOLOv5)      │      0-100 数值      │     (MCU)       │                 │   (左/右)       │
└─────────────────┘                     └─────────────────┘                 └─────────────────┘
```
# System Architecture

## Overview

Array ADB is a modular research platform exploring adaptive LED matrix
high-beam control using pixel-addressable automotive LEDs.

The system consists of:
- Pixel LED driving layer
- Beam control logic
- Vision-assisted decision input
- Vehicle signal abstraction

---

## Hardware Stack

### LED & Driver

- Samsung PixCell LED (pixel-addressable automotive LED)
- Custom-designed LED driver and control board
- Independent pixel-level on/off and timing control
- Thermal and electrical limits enforced in firmware

### Optical System

- OEM projection lenses sourced from:
  - Tesla Model 3 headlight
  - Tesla Model Y headlight
- Dual bi-functional projector configuration
- Optics reused strictly for laboratory evaluation

---

## Vision System

- Camera module: **MaixCam Pro**
- AI compute capability: **up to 1 TOPS**
- Primary functions:
  - Ambient brightness estimation
  - Scene-level awareness input
- Vision output is used as an **assist signal**, not a safety-certified source

No claims are made regarding autonomous perception or object classification accuracy.

---

## Control Flow

Vision Input (Brightness / Scene State)
        ↓
ADB Decision Logic
        ↓
Pixel Mask / Beam Pattern
        ↓
PixCell LED Driver Output
        ↓
Optical Projection

---

## Vehicle Interface (Abstracted)

- CAN / LIN signals (implementation-dependent)
- Signals are treated as generic inputs
- No OEM firmware or proprietary databases included

---

## Design Goals

- Research pixel-level beam shaping behavior
- Evaluate vision-assisted ADB strategies
- Maintain hardware and software modularity
- Avoid OEM dependency or proprietary coupling

---

## Non-Goals

- Road-legal certification
- Production-ready automotive deployment
- OEM-equivalent perception or safety guarantees


## Legal & Safety Disclaimer

This project is provided strictly for:

- Research
- Educational use
- Engineering evaluation

### NOT Intended For

- Public road use
- Commercial deployment
- OEM integration
- Safety-critical automotive systems

### Regulatory Compliance

This project does **NOT** claim compliance with:
- ECE regulations
- SAE standards
- DOT requirements
- Any regional automotive lighting laws

Any use of this project on public roads may be illegal.

---

### Intellectual Property Notice

- No OEM firmware, source code, or confidential documentation is included
- All control logic is independently implemented
- References to automotive brands or components are descriptive only

Tesla, Samsung, and other brand names are used solely to identify
hardware sources and do not imply endorsement or affiliation.

---

### Liability

The authors assume **no responsibility** for:
- Personal injury
- Property damage
- Legal consequences
- Regulatory violations

Use at your own risk.

