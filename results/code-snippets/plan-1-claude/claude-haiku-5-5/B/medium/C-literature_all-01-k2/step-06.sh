cd <SANDBOX_TMP> 2>/dev/null || true; cat > <SANDBOX_TMP>/d8.py 2>/dev/null << 'EOF'
print("x")
EOF
echo rc=$?; python3 - << 'EOF'
import numpy, scipy, sympy
print(numpy.__version__, scipy.__version__, sympy.__version__)
EOF