![ROAR Logo](images/png/ROAR_LOGO.png)

# ROAR

The Robust and Optimal Analog Reuse (ROAR) flow/tool is developed to enable a GUI based approach to the C/ID and gm/ID (I like to say Inverse ID) analog circuit design methodologies. This software enables the the ability to design, optimize, and generate process/technology agnostic design scripts in a graphical yet automated fashion.

## Quick Start (one line)

```tcsh
curl -fsSL https://raw.githubusercontent.com/alecadair/roar/main/bin/install.sh | sh
```

Or if you already have the repo cloned:

```tcsh
cd /path/to/roar && make install
```

## Installation

To set up the ROAR environment, follow these steps (Linux/tcsh):

Prerequisite: Python 3.9 or newer must be available on your system PATH.

1. **One-time setup script (recommended)**

   ```tcsh
   cd /path/to/roar
   ./bin/setup_roar.csh
   ```

   If you previously created `.venv` with an older Python (for example 3.6), recreate it first:

   ```tcsh
   cd /path/to/roar
   rm -rf .venv
   ./bin/setup_roar.csh
   ```

2. **Manual setup (equivalent)**

   ```tcsh
   cd /path/to/roar
   python3 -m venv .venv
   source .venv/bin/activate.csh
   pip install -r requirements.txt
   make
   ```

3. **Run ROAR**

   ```tcsh
   cd /path/to/roar
   source .venv/bin/activate.csh
   source roar_env.csh
   ./bin/roar
   ```

   You can also use:

   ```tcsh
   ./bin/run_roar.csh
   ```

   **Important:** Even when launching with `./bin/roar` (or a packaged binary that calls it), you must activate the Python virtual environment first.

   If startup fails with a Qt/PyQt symbol error (for example `undefined symbol: ...Qt_6`), rebuild the environment:

   ```tcsh
   cd /path/to/roar
   rm -rf .venv
   ./bin/setup_roar.csh
   source .venv/bin/activate.csh
   source roar_env.csh
   ./bin/roar
   ```

   If the GUI flickers or flashes, test software OpenGL for this session:

   ```tcsh
   setenv QT_OPENGL software
   ./bin/roar
   ```

   If you hit a Qt symbol mismatch on a specific machine, enable ROAR's fallback Qt library path for that session:

   ```tcsh
   setenv ROAR_FORCE_VENV_QT 1
   ./bin/roar
   ```

4. **Build an AppImage (optional)**

   The AppImage builder requires `appimagetool` to be installed, or you can point to it explicitly:

   ```tcsh
   cd /path/to/roar
   setenv APPIMAGETOOL /full/path/to/appimagetool
   ./bin/build_appimage.sh
   ```

   For a clean rebuild of the local environment before packaging, use:

   ```tcsh
   ./bin/rebuild_roar.csh --appimage
   ```

## Purpose

ROAR is designed to enable and optimize gm/id and c/id based analog circuit design. The primary goal of this software is to streamline the process of analog circuit design, making it easier to optimize and reuse existing designs through an efficient and automated workflow.

## Disclaimer

Some parts of this codebase were generated with assistance from an LLM. All generated code and resulting behavior are reviewed, verified, and tested by a human before release.

