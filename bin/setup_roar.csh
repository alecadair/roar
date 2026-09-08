#!/usr/bin/env tcsh
# One-time setup for ROAR on Linux/tcsh.

set script_dir=`dirname "$0"`
set script_dir=`cd "$script_dir" && pwd`
set roar_home=`cd "$script_dir/.." && pwd`

if ( ! -d "$roar_home" ) then
    echo "Unable to determine ROAR_HOME from script location." >&2
    exit 1
endif

set python_cmd=""
foreach candidate (python3.12 python3.11 python3.10 python3.9 python3.8 python3)
    which "$candidate" >& /dev/null
    if ( $status != 0 ) then
        continue
    endif

    "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >& /dev/null
    if ( $status == 0 ) then
        set python_cmd="$candidate"
        break
    endif
end

if ( "$python_cmd" == "" ) then
    echo "ROAR setup requires Python 3.9 or newer (PyQt6 6.8 dependency)." >&2
    echo "Install Python 3.9+ and rerun ./bin/setup_roar.csh" >&2
    exit 1
endif

set python_version=`$python_cmd --version`
echo "Using $python_version"

set venv_dir="$roar_home/.venv"
if ( ! -d "$venv_dir" ) then
    echo "Creating Python virtual environment at $venv_dir"
    "$python_cmd" -m venv "$venv_dir"
    if ( $status != 0 ) then
        echo "Failed to create virtual environment." >&2
        exit 1
    endif
endif

if ( ! -x "$venv_dir/bin/python3" ) then
    echo "Missing $venv_dir/bin/python3" >&2
    echo "Delete $venv_dir and rerun setup." >&2
    exit 1
endif

"$venv_dir/bin/python3" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >& /dev/null
if ( $status != 0 ) then
    echo "Existing virtual environment uses unsupported Python (<3.9)." >&2
    echo "Run: rm -rf $venv_dir" >&2
    echo "Then rerun: ./bin/setup_roar.csh" >&2
    exit 1
endif

if ( ! -f "$venv_dir/bin/activate.csh" ) then
    echo "Missing $venv_dir/bin/activate.csh" >&2
    exit 1
endif

source "$venv_dir/bin/activate.csh"

"$venv_dir/bin/python3" -m pip install --upgrade pip
if ( $status != 0 ) then
    echo "Failed to upgrade pip inside virtual environment." >&2
    exit 1
endif

"$venv_dir/bin/python3" -m pip install -r "$roar_home/requirements.txt"
if ( $status != 0 ) then
    echo "Failed to install Python dependencies from requirements.txt." >&2
    echo "ROAR requires Python 3.9+ for PyQt6 6.8." >&2
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

