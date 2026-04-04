# Multimodal Analysis of Interaction with the QT Robot: Interactive Pipeline and Haptic Integration

[![Français](https://img.shields.io/badge/Langue-Français-blue.svg)](docs/README_FR.md)

![QT Robot](docs/robot.png)

## Overview

This repository contains the code to execute an interactive pipeline with the [QT Robot](https://luxai.com/), featuring three distinct scenarios. 

This project was developed as part of a Master 1 (M1) program at the **Université de Montpellier**, supervised by **Madalina Croitoru** and **Ganesh Gowrishankar**. 
The main objective is to design and validate the integration of a haptic vest using a bimodal pipeline (vision and touch) to interact with children.

**Defense Title:** *Analyse Multimodale de l'Interaction avec le Robot QT: Pipeline interactif et intégration haptique*

## Installation & Usage

There are two primary ways to run this project: on a standard Windows machine (for testing/development) or directly on the QT Robot.

### 1. On a standard computer (Windows)

This mode runs the pipeline without the haptic vest or the ROS environment. The pipeline uses standard output prints to compensate for the missing physical interactions.

```cmd
git clone https://github.com/Juste-Leo2/QTRobot-Interaction.git
cd QTRobot-Interaction

setup_env_win.bat
run_win.bat
```

### 2. On the QT Robot

**Hardware Preparation:**
For the haptic vest connections, please refer to the [QT-Touch Repository](https://github.com/Juste-Leo2/QT-Touch/blob/main/raspberry_inference/README.md).

```bash
git clone https://github.com/Juste-Leo2/QTRobot-Interaction.git
cd QTRobot-Interaction

chmod +x setup_env_qt.sh
./setup_env_qt.sh
```
*This command installs the `apt` prerequisites, `uv`, creates the environment, and installs dependencies.*

Once done, directly run:
```bash
uv run main.py --QT --scenario 1
```
*(You can choose scenario `1`, `2`, or `3`)*

**Additional Options:**
- Add the `--follow` argument to enable face tracking for the QT Robot.

## Acknowledgements

Special thanks to:
- My project tutors
- The open source community: [Piper TTS](https://github.com/rhasspy/piper), [PyTorch](https://pytorch.org/)
- The Lux AI team for the development of the vest
- Aalto University in Finland for providing the haptic vest

## License

This project is licensed under the [Apache License 2.0](LICENSE).
