from d6 import *
# check d2 free ion: Racah B=(9F2-5F4)/441, C=35F4/441
F2,F4=1.0,0.6
H,_=build_H(0,F2,F4,nel=2)
ev=np.linalg.eigvalsh(H)
B=(9*F2-5*F4)/441; C=35*F4/441
print('d2 levels', np.round(np.unique(np.round(ev,6)),5))
print('B,C',B,C, 'C/B',C/B)
