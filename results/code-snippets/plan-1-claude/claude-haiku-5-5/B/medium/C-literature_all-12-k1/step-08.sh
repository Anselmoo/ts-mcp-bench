python3 -c "
import ts,numpy as np
print(np.round(ts.Hcf if hasattr(ts,'Hcf') else 0,3))
b=ts.occ_states(7,3); print(b[:3])
M_cf,M=ts.build(b)
print(np.round(M_cf,2))
print(np.trace(M_cf))
"