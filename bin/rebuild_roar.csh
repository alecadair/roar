#!/usr/bin/env tcsh
# Clean rebuild helper for ROAR.
# Recreates the Python environment and optionally builds the AppImage release artifact.

set script_dir=`dirname "$0"`
set script_dir=`cd "$script_dir" && pwd`
set roar_home=`cd "$script_dir/.." && pwd`

if ( ! -d "$roar_home" ) then
    echo "Unable to determine ROAR_HOME from script location." >&2
    exit 1
endif

set build_appimage = 0
foreach arg ($argv)
    switch ( "$arg" )
        case --appimage:
            set build_appimage = 1
            breaksw
        case --help:
            echo "Usage: $0 [--appimage]"
            echo "  --appimage   Also build bin/ROAR-<arch>.AppImage after setup"
            exit 0
        default:
            echo "Unknown option: $arg" >&2
            echo "Usage: $0 [--appimage]" >&2
            exit 1
    endsw
end

if ( -d "$roar_home/.venv" ) then
    echo "Removing existing virtual environment: $roar_home/.venv"
    rm -rf "$roar_home/.venv"
    if ( $status != 0 ) then
        echo "Failed to remove existing virtual environment." >&2
        exit 1
    endif
endif

if ( -d "$roar_home/.appimage-build" ) then
    echo "Removing previous AppImage build workspace: $roar_home/.appimage-build"
    rm -rf "$roar_home/.appimage-build"
    if ( $status != 0 ) then
        echo "Failed to remove previous AppImage build workspace." >&2
        exit 1
    endif
endif

echo "Rebuilding ROAR environment in $roar_home"
"$roar_home/bin/setup_roar.csh"
if ( $status != 0 ) then
    echo "ROAR environment rebuild failed." >&2
    exit 1
endif

if ( $build_appimage ) then
    echo "Building AppImage release artifact"
    "$roar_home/bin/build_appimage.sh"
    if ( $status != 0 ) then
        echo "AppImage build failed." >&2
        exit 1
    endif
endif

echo ""
echo "Rebuild complete."
if ( $build_appimage ) then
    echo "AppImage artifact is under $roar_home/bin/"
else
    echo "To launch ROAR:"
    echo "  cd $roar_home"
    echo "  source .venv/bin/activate.csh"
    echo "  source roar_env.csh"
    echo "  ./bin/roar"
endif

