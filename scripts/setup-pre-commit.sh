#!/bin/bash
# Setup script for pre-commit hooks

set -euo pipefail

echo "🔧 Setting up pre-commit hooks for EX-AI MCP Server..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Please run this from the project root."
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH."
    exit 1
fi

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
else
    echo "✅ pre-commit is already installed"
fi

# Install the pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Install commit-msg hook for conventional commits
echo "📝 Installing commit-msg hook..."
pre-commit install --hook-type commit-msg

# Run pre-commit on all files to ensure everything works
echo "🧪 Running pre-commit on all files..."
pre-commit run --all-files || {
    echo "⚠️  Some pre-commit checks failed. This is normal for the first run."
    echo "   The hooks will automatically fix many issues."
    echo "   Please review the changes and commit them."
}

echo ""
echo "✅ Pre-commit hooks setup complete!"
echo ""
echo "📋 What happens now:"
echo "   • Pre-commit hooks will run automatically on every commit"
echo "   • Code will be automatically formatted with black and isort"
echo "   • Security scans will run with bandit"
echo "   • Linting will run with ruff"
echo "   • Type checking will run with mypy"
echo ""
echo "🚀 To manually run all hooks: pre-commit run --all-files"
echo "🔧 To update hooks: pre-commit autoupdate"
echo ""
echo "Happy coding! 🎉"
