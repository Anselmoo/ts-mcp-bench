
cd /tmp/tsbench-run-9aa2jt5t 2>/dev/null; cd ~/w 2>/dev/null || cd /dev/shm; sed -i 's/\*(-1)\*\*(a-cc) for k/ for k/' a.py; grep -n "for k in (2,4)" a.py; python3 a.py