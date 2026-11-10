cd /tmp && python3 - << 'EOF'
import numpy as np
exec(open('/dev/null').read())
EOF
echo; python3 - << 'EOF'
import numpy as np
# values from previous run recomputed inline for scan
EOF
echo "rerun scan"