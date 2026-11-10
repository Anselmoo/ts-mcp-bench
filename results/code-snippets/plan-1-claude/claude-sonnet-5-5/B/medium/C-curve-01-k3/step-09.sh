cd <SANDBOX_TMP>; sed 's/combinations(range(n),4)/combinations(range(n),2)/' a.py | python3 -c "
import sys
src=sys.stdin.read().split('\nfor x in (0.9')[0]
exec(src)
print(V(2,2,2,2),V(2,1,2,1),V(2,1,1,2),V(2,-2,2,-2))
print(orbs)
"