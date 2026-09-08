![ROAR Logo](images/png/ROAR_LOGO.png)

# ROAR

Robust and Optimal Analog Reuse (ROAR) is a GUI-based tool for analog circuit design using C/ID and gm/ID methodologies. Design, optimize, and generate process-agnostic design scripts efficiently.

## Install

Requires Python 3.9 or newer.

```tcsh
git clone https://github.com/alecadair/roar.git
cd roar
make install
```

## Run

```tcsh
cd roar
source .venv/bin/activate.csh
source roar_env.csh
./bin/roar
```

Or simply:

```tcsh
./bin/run_roar.csh
```

## Manual Install

```tcsh
cd /path/to/roar
./bin/setup_roar.csh
```

## Disclaimer

Some parts of this codebase were generated with assistance from an LLM. All generated code and resulting behavior are reviewed, verified, and tested by a human before release.

