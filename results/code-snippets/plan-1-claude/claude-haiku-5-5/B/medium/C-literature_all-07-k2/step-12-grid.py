import numpy as np
from model import model
for Dq in [500,700,900]:
  for B in [600,800]:
    for CB in [4.0,4.5]:
        p=[Dq,B,CB*B]
        T,E=model(p)
        print(p, np.round(T[:3]), np.round(E[:2]), flush=True)
