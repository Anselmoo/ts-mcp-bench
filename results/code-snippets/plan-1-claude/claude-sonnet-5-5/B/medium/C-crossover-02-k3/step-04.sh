
f=$(find / -name a.py -newer /etc/hostname 2>/dev/null | head -1); echo $f; cd $(dirname $f); sed -i 's/\*(-1)\*\*(a-cc) for k/ for k/' a.py; python3 a.py