python3 -c "
import d3,numpy as np
print(len(d3.VC), list(d3.VC.items())[:3])
print(np.linalg.norm(d3.C[0]), np.linalg.norm(d3.CD[0]), len(d3.idx3))
print(d3.ak(2,0,0,0,0), d3.ak(0,0,0,0,0))
"