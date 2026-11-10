cd /; python3 -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)"; echo; python3 - << 'EOF'
print("stdin python works")
EOF