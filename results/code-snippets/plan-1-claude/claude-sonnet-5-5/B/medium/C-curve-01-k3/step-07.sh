cd <SANDBOX_TMP>; python3 -c "
exec(open('a.py').read().split('\nfor x in (0.9')[0])
e=run(0);e-=e[0]
import collections
print(collections.Counter(np.round(e/B,2)))"