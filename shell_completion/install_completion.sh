#!/bin/bash
#==============================================================================
# Shell Completion Installation Script for zoidoffice
# 
# This script installs bash/zsh shell completion for the zoidoffice command.
# It requires argcomplete to be installed: pip install argcomplete
#==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================================================="
echo "zoidoffice Shell Completion Installer"
echo "=============================================================================="

# Check if argcomplete is installed
if ! command -v register-python-argcomplete &> /dev/null; then
    echo -e "${YELLOW}argcomplete is not installed.${NC}"
    echo "Please install it with: pip install argcomplete"
    exit 1
fi

# Detect available shells
install_bash=false
install_zsh=false

# Bash installation
if [ -d /etc/bash_completion.d ]; then
    install_bash=true
elif [ -w ~/.bash_completion.d ]; then
    install_bash=true
fi

# Zsh installation  
if [ -d /usr/local/share/zsh/site-functions ]; then
    if [ -w /usr/local/share/zsh/site-functions ] || [ "$(id -u)" = "0" ]; then
        install_zsh=true
    fi
elif [ -d ~/.zsh/functions ]; then
    install_zsh=true
fi

echo ""
echo "Available shells detected:"
$install_bash && echo "  - Bash: Yes (system-wide: /etc/bash_completion.d)" || echo "  - Bash: No (not writable)"
$install_zsh && echo "  - Zsh: Yes (system-wide: /usr/local/share/zsh/site-functions)" || echo "  - Zsh: No (not writable)"

# Function to register completion
register_completion() {
    local shell=$1
    local output_path=$2
    
    echo "Installing for $shell..."
    
    if register-python-argcomplete --shell "$shell" zoidoffice > "$output_path" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Installed $shell completion to $output_path"
        
        # For bash, also try to source it
        if [ "$shell" = "bash" ]; then
            # Test if we can source it
            if source "$output_path" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} $shell completion sourced successfully"
            fi
        fi
        
        return 0
    else
        echo -e "${RED}✗${NC} Failed to install $shell completion"
        return 1
    fi
}

# Install bash completion
if $install_bash; then
    if [ "$(id -u)" = "0" ]; then
        register_completion "bash" "/etc/bash_completion.d/zoidoffice"
    else
        mkdir -p ~/.bash_completion.d
        register_completion "bash" ~/.bash_completion.d/zoidoffice
        echo ""
        echo "Add to your ~/.bashrc:"
        echo "  source ~/.bash_completion.d/zoidoffice"
    fi
fi

# Install zsh completion  
if $install_zsh; then
    register_completion "zsh" "/usr/local/share/zsh/site-functions/_zoidoffice"
fi

echo ""
echo "=============================================================================="
echo "Installation complete!"
echo "=============================================================================="
echo ""
echo "To use completion in your current shell:"
echo "  eval \"\$(register-python-argcomplete zoidoffice)\""
echo ""
echo "To enable completion permanently, add the above line to your shell's RC file."
