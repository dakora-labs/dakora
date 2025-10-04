#!/usr/bin/env bash
# Quick setup script for Microsoft Agent Framework integration example
# Run this to get started quickly

echo "============================================"
echo "Dakora + Microsoft Agent Framework Setup"
echo "============================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1)
if [[ $python_version =~ Python\ 3\.([0-9]+) ]]; then
    minor_version=${BASH_REMATCH[1]}
    if [ $minor_version -lt 10 ]; then
        echo "❌ Python 3.10+ required. You have: $python_version"
        exit 1
    fi
    echo "✓ Python version OK: $python_version"
    echo ""
else
    echo "❌ Python not found or version check failed"
    exit 1
fi

# Create virtual environment
echo "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    if [ $? -eq 0 ]; then
        echo "✓ Virtual environment created"
        echo ""
    else
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
else
    echo "✓ Virtual environment already exists"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo "✓ Virtual environment activated"
    echo ""
else
    echo "⚠️  Could not activate virtual environment automatically"
    echo "   Please run: source venv/bin/activate"
    echo ""
fi

# Install dependencies
echo "Installing dependencies in virtual environment..."
echo "   (Note: Microsoft Agent Framework is in beta - this may take a moment)"
echo ""
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
    echo ""
else
    echo "❌ Failed to install dependencies"
    echo ""
    echo "⚠️  Troubleshooting tips:"
    echo "   1. Microsoft Agent Framework is currently in beta"
    echo "   2. Try installing manually:"
    echo "      pip install agent-framework agent-framework-azure --pre"
    echo "   3. Or install specific beta version:"
    echo "      pip install agent-framework==1.0.0b251001 agent-framework-azure==1.0.0b251001"
    echo ""
    echo "   4. If packages aren't available, check:"
    echo "      https://pypi.org/project/agent-framework/#history"
    echo ""
    exit 1
fi

# Check Azure CLI
echo "Checking Azure CLI..."
if command -v az &> /dev/null; then
    echo "✓ Azure CLI found"
    echo ""
else
    echo "⚠️  Azure CLI not found. Install from: https://aka.ms/azure-cli"
    echo "   You can still use this example with API key authentication"
    echo ""
fi

# Check Azure login status
echo "Checking Azure login status..."
if az account show &> /dev/null; then
    echo "✓ Azure CLI authenticated"
    echo ""
else
    echo "⚠️  Not logged in to Azure. Run: az login"
    echo "   Or set AZURE_OPENAI_API_KEY environment variable"
    echo ""
fi

# Initialize Dakora
echo "Initializing Dakora..."
if [ ! -f "dakora.yaml" ]; then
    dakora init
    if [ $? -eq 0 ]; then
        echo "✓ Dakora initialized"
        echo ""
    else
        echo "⚠️  Could not initialize Dakora automatically"
        echo "   The examples will still work (they auto-create templates)"
        echo ""
    fi
else
    echo "✓ Dakora already initialized"
    echo ""
fi

# Check environment variables
echo "Checking environment configuration..."

# Check if .env.example exists and .env doesn't
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    echo "📋 Found .env.example but no .env file"
    echo "   Creating .env from template..."
    echo ""
    cp .env.example .env
    echo "✓ Created .env file - please edit it with your Azure credentials!"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and set your AZURE_OPENAI_ENDPOINT"
    echo ""
fi

if [ -n "$AZURE_OPENAI_ENDPOINT" ] || [ -n "$AZURE_AI_PROJECT_ENDPOINT" ]; then
    echo "✓ Azure endpoint configured"
    echo ""
    [ -n "$AZURE_OPENAI_ENDPOINT" ] && echo "   AZURE_OPENAI_ENDPOINT: $AZURE_OPENAI_ENDPOINT" && echo ""
    [ -n "$AZURE_AI_PROJECT_ENDPOINT" ] && echo "   AZURE_AI_PROJECT_ENDPOINT: $AZURE_AI_PROJECT_ENDPOINT" && echo ""
else
    echo "⚠️  No Azure endpoints configured"
    echo "   You have two options:"
    echo ""
    echo "   Option 1: Edit .env file (recommended):"
    echo "   - Open .env in your editor"
    echo "   - Set AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com"
    echo ""
    echo "   Option 2: Set environment variable directly:"
    echo "   export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'"
    echo ""
fi

# Summary
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""

echo "⚡ Your virtual environment is ready!"
echo "   Location: ./venv"
echo ""

echo "Next steps:"

echo "1. Activate the virtual environment (if not already active):"
echo "   source venv/bin/activate"
echo ""

echo "2. Configure Azure credentials:"
echo "   a) Edit .env file with your Azure OpenAI endpoint:"
echo "      AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com"
echo ""
echo "   b) Login to Azure CLI (for authentication):"
echo "      az login"
echo ""

echo "3. Run the simple example:"
echo "   python simple_agent_example.py"
echo ""

echo "4. Or run the multi-agent example:"
echo "   python multi_agent_example.py"
echo ""

echo "5. Explore and edit templates with Dakora Playground:"
echo "   dakora playground"
echo ""

echo "6. When done, deactivate the virtual environment:"
echo "   deactivate"
echo ""

echo "💡 Tip: The virtual environment keeps dependencies isolated from your system Python."
echo "   This is best practice for Python projects!"
echo ""

echo "For help, see README.md or visit:"
echo "https://github.com/bogdan-pistol/dakora"
echo ""
