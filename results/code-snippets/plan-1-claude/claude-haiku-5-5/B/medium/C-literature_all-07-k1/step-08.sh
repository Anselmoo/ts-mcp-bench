cat > /dev/null << 'EOF'
EOF
cd / 2>/dev/null; python3 -c "import os; print(os.getcwd(), os.access('.', os.W_OK))"; python3 -c "import tempfile; print(tempfile.gettempdir())"