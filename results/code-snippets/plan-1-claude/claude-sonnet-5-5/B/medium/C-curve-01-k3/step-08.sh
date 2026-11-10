cd <SANDBOX_TMP>; sed 's/combinations(range(n),4)/combinations(range(n),2)/' a.py | python3 -c "
import sys
src=sys.stdin.read().split('\nfor x in (0.9')[0]
exec(src)
import collections
e=run(0);e-=e[0]
print(collections.Counter(np.round(e/B,2)))"