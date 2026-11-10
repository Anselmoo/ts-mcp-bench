cd /dev/shm && python3 -c "
from ts import *
H=build(0,1.0,0.0)
print('herm',np.abs(H-H.T).max())
V=Vspat({2:49.0,4:0.0})
print(np.round(V[0,4,0,4],4), np.round(V[1,1,1,1],4), np.round(V[4,4,4,4],4))
print(np.round(V[0,4,4,0],4), np.round(V[0,4,0,4],4))
print(np.abs(V-V.transpose(1,0,3,2)).max())
" 2>&1 | tail -8