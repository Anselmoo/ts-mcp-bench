cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
exec(open('/dev/stdin').read()) if False else None
EOF
cd /tmp && cat > /dev/null << 'EOF'
EOF
echo "rerun needed"