cd /dev/shm && python3 -c "
from ts import *
w,S,U,H=spectrum(0,1,0)
print('trace B-only', np.trace(H))
w,S,U,H=spectrum(0,0,1)
print('trace C-only', np.trace(H))
V=Vspat({2:1.0,4:0.0})
# monopole check: sum over b of <ab|g|ab> should be 2*? F2 part average zero
print('avg direct F2', sum(V[a,b,a,b] for a in range(5) for b in range(5))/25, 'avg exch', sum(V[a,b,b,a] for a in range(5) for b in range(5))/25)
"