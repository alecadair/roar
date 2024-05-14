#
# Author: Alec S. Adair
# ROAR - Turku, Finland
#
# Intended to run with Centos/Redhat operating systems and tcsh or csh
#

SHELL = /usr/local/bin/tcsh
CURRENT_DIRECTORY := $(shell pwd)

all: generate_roar_env

generate_roar_env:
	@echo "Generating ROAR Environment File: roar_env.csh"
	@echo "If running ROAR from source code, roar_env.csh must be sourced before running ROAR"
	@echo "source roar_env.csh "
	@echo "This sets environmental variables needed for ROAR flow"
	@echo "The contents of roar_env.csh can be appended to your .bashrc script."
	@echo "If the contents of roar_env.csh are not appended to your .bashrc then"
	@echo "roar_env.csh needs to be sourced every time before running ROAR."

	@echo "#" > roar_env.csh
	@echo -n "# File generated on " >> roar_env.csh 
	@date >> roar_env.csh
	@echo "#" >> roar_env.csh
	@echo "" >> roar_env.csh

	@setenv WORKING_DIRECTORY "$(CURRENT_DIRECTORY)"; \
	echo "setenv ROAR_HOME $$WORKING_DIRECTORY" >> roar_env.csh
	@echo 'setenv ROAR_SRC $$ROAR_HOME/src' >> roar_env.csh
	@echo 'setenv ROAR_DESIGN_SCRIPTS $$ROAR_HOME/design_scripts' >> roar_env.csh
	@echo 'setenv ROAR_LIB $$ROAR_HOME/lib' >> roar_env.csh
	@echo 'setenv ROAR_CHARACTERIZATION $$ROAR_HOME/characterization' >> roar_env.csh

	@echo '' >> roar_env.csh
	@chmod +x roar_env.csh


clean:
	@rm -f roar_env.csh

