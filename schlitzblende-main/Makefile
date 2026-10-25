# Set the repository URL
REPO_URL = https://gitlab.com/yukidama/kicad-sharedlib.git
# Set the target folder
LIB_DIR = Lib

# Makefile

# Set the default target
.DEFAULT_GOAL := all

# Detect the operating system
ifeq ($(OS),Windows_NT)
    RM := del /Q
    MKDIR := mkdir
else
    RM := rm -f
    MKDIR := mkdir -p
endif

.PHONY: all
all: | $(LIB_DIR)
	@echo "All targets built."

$(LIB_DIR):
	@echo "Cloning the Git repo into $(LIB_DIR)..."
	git clone $(REPO_URL) $(LIB_DIR)

.PHONY: clean
clean:
	@echo "Cleaning up..."
	-$(RM) $(LIB_DIR)

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all       : Build all targets"
	@echo "  clean     : Remove generated files"
	@echo "  help      : Display this help message"

# Suppress make's default rules and recipes
.SUFFIXES: