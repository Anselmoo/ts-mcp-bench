cat >> a.py <<'E'
import collections
print(sorted(collections.Counter(np.round(ham(2,0),1)).items()))
E
python3 a.py | tail -1