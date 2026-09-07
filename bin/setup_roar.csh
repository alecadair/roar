#!/usr/bin/env tcsh
# One-time setup for ROAR on Linux/tcsh.

set script_dir=`dirname "$0"`
set script_dir=`cd "$script_dir" && pwd`
set roar_home=`cd "$script_dir/.." && pwd`

if ( ! -d "$roar_home" ) then
    echo "Unable to determine ROAR_HOME from script location." >&2
    exit 1
endif

set venv_dir="$roar_home/.venv"
if ( ! -d "$venv_dir" ) then
    echo "Creating Python virtual environment at $venv_dir"
    python3 -m venv "$venv_dir"
    if ( $status != 0 ) then
        echo "Failed to create virtual environment." >&2
        exit 1
    endif
endif

if ( ! -f "$venv_dir/bin/activate.csh" ) then
    echo "Missing $venv_dir/bin/activate.csh" >&2
    exit 1
endif

source "$venv_dir/bin/activate.csh"

python3 -m pip install --upgrade pip
if ( $status != 0 ) then
    echo "Failed to upgrade pip inside virtual environment." >&2
    exit 1
endif

python3 -m pip install -r "$roar_home/requirements.txt"
if ( $status != 0 ) then
    echo "Failed to install Python dependencies." >&2
    exit 1
endif

make -C "$roar_home"
if ( $status != 0 ) then
    echo "make failed while generating ROAR environment files." >&2
    exit 1
endif

echo ""
echo "ROAR setup complete. Use these commands in each new terminal:"
echo "  cd $roar_home"
echo "  source .venv/bin/activate.csh"
echo "  source roar_env.csh"
echo "  $roar_home/bin/roar"

