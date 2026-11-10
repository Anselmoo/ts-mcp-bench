import numpy as np
from ham import build
# d2 test: 3P-3F should be 15B; with F2,F4 -> B=(9F2-5F4)/441, C=35F4/441
F2,F4=1.0,0.625
b,H = build(2,0,0,F2,F4)
e = np.linalg.eigvalsh(H)
B=(9*F2-5*F4)/441; C=35*F4/441
print(np.unique(np.round(e,4)))
print('B',B,'C',C)
