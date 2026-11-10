sed -i "s/r=apply_ops(\[('c',a),('a',b)\],s)/r=apply_ops([('a',b),('c',a)],s)/" ts.py && grep -n "apply_ops(\[('a',b)" ts.py && python3 -c "
import ts,numpy as np
b=ts.occ_states(7,3)
M_cf,M=ts.build(b)
print(np.round(np.linalg.eigvalsh(M_cf),3))
for k in (0,2,4): print(k,np.round(np.linalg.eigvalsh(M[k]),3))
"