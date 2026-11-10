import numpy as np, ts
d = ts.build(4,1.0,4.79)
Rz = d['Rot']([0,0,1.],np.pi/2)
Rc = d['Rot']([1,1,1.],2*np.pi/3)
print(np.allclose(Rz@Rz@Rz@Rz, np.eye(len(Rz))))
print(np.allclose(np.linalg.matrix_power(Rc,3), np.eye(len(Rz))))
Hcf = d['Hcf']; print(np.allclose(Rz.conj().T@Hcf@Rz, Hcf), np.allclose(Rc.conj().T@d['Hee']@Rc, d['Hee']))
print(np.allclose(Rz.conj().T@Rz, np.eye(len(Rz))))
print(np.trace(Rz), np.trace(Rc), np.trace(d['Rot']([0,0,1.],np.pi)))
