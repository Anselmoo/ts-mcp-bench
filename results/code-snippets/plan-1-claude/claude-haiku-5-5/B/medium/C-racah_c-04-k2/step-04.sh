
cat << 'EOF' | python3 - 
import numpy as np, itertools
exec(open('/dev/stdin').read()) if False else None
EOF
echo skip