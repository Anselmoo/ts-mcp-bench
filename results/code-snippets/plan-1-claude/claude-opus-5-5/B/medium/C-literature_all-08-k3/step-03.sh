
cd /tmp && D=$(mktemp -d) && cd $D && sed 's/for x in (q,p):/for x in (p,q):/' /dev/stdin > /dev/null; ls /tmp/tsbench-run-o3p_lij2 2>/dev/null | head; find /tmp -name d5.py 2>/dev/null