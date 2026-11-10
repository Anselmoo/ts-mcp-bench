
cd "$(pwd)" && python3 -c "
exec(open('fit.py').read().split('if __name__')[0])
from collections import Counter
F2=49*600+7*2400; F4=63*2400/5
H=1750*Ocf+F2*O2+F4*O4
e,v=np.linalg.eigh(H)
print(Counter(np.round(e,0)).most_common(30))
" 2>&1 | tail -1
