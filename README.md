![ROAR Logo](images/png/ROAR_LOGO.png)

# ROAR

The Robust and Optimal Analog Reuse (ROAR) flow/tool is developed to enable a GUI based approach to the C/ID and gm/ID (I like to say Inverse ID) analog circuit design methodologies. This software enables the the ability to design, optimize, and generate process/technology agnostic design scripts in a graphical yet automated fashion.

## Requirements

- **Python 3.9** or newer
- **tcsh** or **csh** shell
- **git** for cloning the repository
- Linux/Unix environment (tested on Rocky Linux, CentOS, Ubuntu)

## Install

```tcsh
git clone https://github.com/alecadair/roar.git
cd roar
make install
```

This will:
1. Create a Python virtual environment (`.venv`)
2. Install all dependencies from `requirements.txt`
3. Generate the ROAR environment configuration file

## Run

ROAR requires the Python virtual environment and shell environment to be activated before running:

```tcsh
cd roar
source .venv/bin/activate.csh
source roar_env.csh
./bin/roar
```

Or use the convenience launcher that handles activation automatically:

```tcsh
./bin/run_roar.csh
```

**Important:** You must run these commands in **tcsh** or **csh**, not bash or sh.

## Manual Install

If you prefer to set up manually:

```tcsh
cd /path/to/roar
./bin/setup_roar.csh
```

Then to run:

```tcsh
source .venv/bin/activate.csh
source roar_env.csh
./bin/roar
```

## Virtual Environment

The virtual environment is created in `.venv/` during installation. It contains all Python dependencies for ROAR. You must activate it before running:

```tcsh
source .venv/bin/activate.csh
```

If you move the installation directory, the virtual environment should be recreated:

```tcsh
rm -rf .venv
make install
```

## Disclaimer

Some parts of this codebase were generated with assistance from an LLM. All generated code and resulting behavior are reviewed, verified, and tested by a human before release.

