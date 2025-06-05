# Dual-SIRC-Blaster

This repository contains a simple Python tool for sending Sony SIRC IR commands
using the [Obniz](https://obniz.com) platform. It can operate in mock mode for
dev and testing without hardware.

## Usage

1. Install dependencies:
   ```bash
   pip install typer python-dotenv
   ```
2. Create a `.env` file with your Obniz device IDs and mock flag:
   ```ini
   OBNIZ_IDS=YOUR_ID_A,YOUR_ID_B
   OBNIZ_MOCK=1  # set to 0 when using real hardware
   ```
3. Run the CLI:
   ```bash
   python dual_sirc.py blast demo
   ```
   Modes `ready`, `start`, and `stop` send individual commands.

Run `pytest` to execute unit tests. They run in mock mode by default.
