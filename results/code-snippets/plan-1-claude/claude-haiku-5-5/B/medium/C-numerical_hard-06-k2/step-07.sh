cat > /dev/null <<'EOF'
EOF
python3 - <<'EOF'
import numpy as np, itertools
exec(open('/dev/stdin').read()) if False else None
EOF
echo skip