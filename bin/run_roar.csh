#!/usr/bin/env tcsh
# Convenience launcher that enforces venv activation, then runs ROAR.

set script_dir=`dirname "$0"`
set script_dir=`cd "$script_dir" && pwd`
set roar_home=`cd "$script_dir/.." && pwd`

if ( ! $?VIRTUAL_ENV ) then
    echo "ROAR requires an active Python virtual environment." >&2
    echo "Run: source $roar_home/.venv/bin/activate.csh" >&2
    exit 1
endif

if ( ! -f "$roar_home/roar_env.csh" ) then
    echo "Missing $roar_home/roar_env.csh. Run: make -C $roar_home" >&2
    exit 1
endif

source "$roar_home/roar_env.csh"
exec "$roar_home/bin/roar" $argv:q

