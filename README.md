# Array ADB

Adaptive LED Matrix High Beam **Research Platform**  
for Samsung PixCell LED

Array ADB is an experimental automotive lighting research project focused on
pixel-addressable LED control and adaptive driving beam (ADB) behavior.

⚠️ Research & evaluation only. Not street-legal.

---

## Overview

This project explores **adaptive LED matrix high-beam control** using
Samsung PixCell LEDs, custom control hardware, and vision-assisted decision logic.

The goal is to evaluate pixel-level beam shaping strategies and system
architectures for next-generation automotive lighting.

---

## Key Features

- Samsung PixCell LED control algorithm
- Custom-designed LED driver and control hardware
- Adaptive LED Matrix High Beam (ADB-style logic)
- Pixel-level beam masking and timing control
- Vision-assisted input for experimental decision making
- Modular firmware and hardware architecture

---

## Optical System

- OEM projection lenses sourced from **Tesla Model 3 / Model Y** headlights
- Used solely for **optical evaluation and beam pattern research**
- Dual bi-functional projector configuration

OEM components are reused strictly for laboratory and research purposes.

---

## Vision System

- Vision device: **MaixCam Pro**
- AI compute capability: **up to 1 TOPS**
- Used for:
  - Ambient brightness estimation
  - Scene-level awareness input

Vision output is **non-safety-critical** and used for
**experimental decision support only**.

No claims are made regarding perception accuracy or autonomous driving capability.

---

## System Architecture (High Level)

Vision Input
→ ADB Decision Logic
→ Pixel Mask Generation
→ PixCell LED Driver
→ Optical Projection

Vehicle signals (e.g. CAN / LIN) are treated as abstract inputs.
No OEM firmware or proprietary databases are included.

---

## Keywords

- Adaptive LED Matrix High Beams  
- ADB (Adaptive Driving Beam)  
- Samsung PixCell LED  
- Automotive Lighting R&D  
- Vision-assisted beam control  

---

## Legal & Safety Disclaimer

This project is provided strictly for:

- Research
- Educational use
- Engineering evaluation

### NOT Intended For

- Public road use
- Commercial deployment
- Production vehicles
- Safety-critical automotive systems

### Regulatory Compliance

This project does **NOT** claim compliance with:
ECE, SAE, DOT, or any regional automotive lighting regulations.

Nothing in this repository constitutes an offer for sale or commercial use.

---

### Intellectual Property Notice

- No OEM firmware, source code, or confidential documentation is included
- All control logic is independently developed
- References to Tesla, Samsung, or other brands are descriptive only

Brand names are used solely to identify hardware sources and do not imply
endorsement or affiliation.

---

### Liability

The authors assume no responsibility for:
- Personal injury
- Property damage
- Legal consequences
- Regulatory violations

Use at your own risk.
