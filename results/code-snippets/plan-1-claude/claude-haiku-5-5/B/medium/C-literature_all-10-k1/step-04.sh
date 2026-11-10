cd /tmp && cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import re,sys
src = open('/dev/stdin').read() if False else None
EOF
echo skip