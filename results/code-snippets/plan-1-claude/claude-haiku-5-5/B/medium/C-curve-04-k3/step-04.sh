cd /dev/shm && mkdir -p d5 && cd d5 && cat << 'EOF' > run.py
exec(open('/dev/shm/d5/d5.py').read())
import sys
EOF
echo