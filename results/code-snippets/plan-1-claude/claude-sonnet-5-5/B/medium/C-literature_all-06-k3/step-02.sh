python3 -c "
import numpy as np
D=2660
for B in range(100,1200,50):
    M=np.array([[6*D,6*B],[6*B,15*B]]);print(B,min(np.linalg.eigvalsh(M))+12*D)
"