#!/usr/bin/env sh
# One-line ROAR installer for users.
# Downloads, sets up, and launches ROAR.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/alecadair/roar/main/bin/install.sh | sh
#
# Or with a specific target directory:
#   TARGET_DIR=~/custom_roar curl -fsSL https://raw.githubusercontent.com/alecadair/roar/main/bin/install.sh | sh

set -eu

# Allow override of install directory
TARGET_DIR="${TARGET_DIR:-$HOME/roar}"

echo "Installing ROAR to $TARGET_DIR"

# Check if already cloned
if [ -d "$TARGET_DIR" ]; then
    echo "ROAR already exists at $TARGET_DIR"
    cd "$TARGET_DIR"
    git pull
else
    git clone https://github.com/alecadair/roar.git "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# Run the setup
echo "Setting up ROAR environment..."
./bin/setup_roar.csh

echo ""
echo "✓ ROAR installation complete!"
echo ""
echo "To launch ROAR, run:"
echo "  cd $TARGET_DIR"
echo "  source .venv/bin/activate.csh"
echo "  source roar_env.csh"
echo "  ./bin/roar"
echo ""
echo "Or use the convenience launcher:"
echo "  cd $TARGET_DIR"
echo "  ./bin/run_roar.csh"

