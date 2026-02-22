#
# Author: Alec S. Adair
# ROAR - Turku, Finland
#
# Generates roar_env.csh for setting ROAR environment variables.
# Works with CentOS, RedHat, Ubuntu, and tcsh/csh.
#

TCSH_PATH := $(shell which tcsh)
SH_PATH := $(shell which bash)


# Ensure tcsh is installed
ifeq ($(TCSH_PATH),)
    $(error "Error: tcsh is not installed or not in the system PATH.")
endif

# Use detected tcsh as the Makefile shell
SHELL := $(TCSH_PATH)
CURRENT_DIRECTORY := $(shell pwd)
OUTPUT_FILE := roar_env.csh
OUTPUT_FILE_SH := roar_env.sh

all: generate_roar_env

generate_roar_env:
	@echo "Generating ROAR Environment File: roar_env.csh"
	@echo "Source it before using ROAR: source roar_env.csh"
	@echo "To make it permanent, add 'source /path/to/roar_env.csh' to ~/.cshrc or ~/.tcshrc."

	@echo "#" > $(OUTPUT_FILE)
	@echo "# ROAR Environment Setup Script" >> $(OUTPUT_FILE)
	@echo "# Generated on `date`" >> $(OUTPUT_FILE)
	@echo "# This script must be sourced to configure the ROAR environment." >> $(OUTPUT_FILE)
	@echo "#" >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'setenv ROAR_HOME "$(CURRENT_DIRECTORY)"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_SRC "$$ROAR_HOME/src"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_DESIGN "$$ROAR_HOME/design"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_LIB "$$ROAR_HOME/lib"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_DEPENDENCIES "$$ROAR_HOME/dependencies"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_CHARACTERIZATION "$$ROAR_HOME/characterization"' >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'if ( ! $$?LD_LIBRARY_PATH ) then' >> $(OUTPUT_FILE)
	@echo '    setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib64"' >> $(OUTPUT_FILE)
	@echo 'else' >> $(OUTPUT_FILE)
	@echo '    setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib64:$$LD_LIBRARY_PATH"' >> $(OUTPUT_FILE)
	@echo 'endif' >> $(OUTPUT_FILE)
	@echo 'setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib:$$LD_LIBRARY_PATH"' >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'echo "ROAR environment variables set."' >> $(OUTPUT_FILE)
	@echo "ROAR environment script generated: $(OUTPUT_FILE)"
	@echo "Run: source $(OUTPUT_FILE) before using ROAR"
	chmod +x bin/roar

generate_roar_env_bash:
	@echo "Generating ROAR Environment File: roar_env.sh"
	@echo "Source it before using ROAR: source roar_env.sh"
	@echo "To make it permanent, add 'source /path/to/roar_env.sh' to ~/.bashrc."

	@echo "#" > $(OUTPUT_FILE)
	@echo "# ROAR Environment Setup Script" >> $(OUTPUT_FILE)
	@echo "# Generated on `date`" >> $(OUTPUT_FILE)
	@echo "# This script must be sourced to configure the ROAR environment." >> $(OUTPUT_FILE)
	@echo "#" >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'setenv ROAR_HOME "$(CURRENT_DIRECTORY)"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_SRC "$$ROAR_HOME/src"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_DESIGN "$$ROAR_HOME/design"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_LIB "$$ROAR_HOME/lib"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_DEPENDENCIES "$$ROAR_HOME/dependencies"' >> $(OUTPUT_FILE)
	@echo 'setenv ROAR_CHARACTERIZATION "$$ROAR_HOME/characterization"' >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'if ( ! $$?LD_LIBRARY_PATH ) then' >> $(OUTPUT_FILE)
	@echo '    setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib64"' >> $(OUTPUT_FILE)
	@echo 'else' >> $(OUTPUT_FILE)
	@echo '    setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib64:$$LD_LIBRARY_PATH"' >> $(OUTPUT_FILE)
	@echo 'endif' >> $(OUTPUT_FILE)
	@echo 'setenv LD_LIBRARY_PATH "$$ROAR_HOME/lib:$$LD_LIBRARY_PATH"' >> $(OUTPUT_FILE)
	@echo "" >> $(OUTPUT_FILE)

	@echo 'echo "ROAR environment variables set."' >> $(OUTPUT_FILE)
	@echo "ROAR environment script generated: $(OUTPUT_FILE)"
	@echo "Run: source $(OUTPUT_FILE) before using ROAR"



clean:
	@rm -f $(OUTPUT_FILE)
	@echo "Cleaned: $(OUTPUT_FILE)"
