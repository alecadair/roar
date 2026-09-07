
# ROAR
The Robust and Optimal Analog Reuse (ROAR) flow/tool is developed to enable a GUI based approach to the C/ID and gm/ID (I like to say Inverse ID) analog circuit design methodologies. This software enables the the ability to design, optimize, and generate process/technology agnostic design scripts in a graphical yet automated fashion.

## Installation

To set up the ROAR environment, follow these steps (Linux/tcsh):

1. **One-time setup script (recommended)**

   ```bash
   cd /path/to/roar
   ./bin/setup_roar.csh
   ```

2. **Manual setup (equivalent)**

   ```bash
   cd /path/to/roar
   python3 -m venv .venv
   source .venv/bin/activate.csh
   pip install -r requirements.txt
   make
   ```

3. **Run ROAR**

   ```bash
   cd /path/to/roar
   source .venv/bin/activate.csh
   source roar_env.csh
   ./bin/roar
   ```

   You can also use:

   ```bash
   ./bin/run_roar.csh
   ```

   **Important:** Even when launching with `./bin/roar` (or a packaged binary that calls it), you must activate the Python virtual environment first.

## Purpose

ROAR is designed to enable and optimize gm/id and c/id based analog circuit design. The primary goal of this software is to streamline the process of analog circuit design, making it easier to optimize and reuse existing designs through an efficient and automated workflow.

## Disclaimer

Some parts of this codebase were generated with assistance from an LLM. All generated code and resulting behavior are reviewed, verified, and tested by a human before release.

