cd <SANDBOX_TMP> && python3 -c "
from a import levels
import numpy as np
for p in ([814.517,878.15,3978.99],[814.517,878.15,2823.35]):
    e=levels(*p);u,c=np.unique(np.round(e,0),return_counts=True);print(p,[(a,b) for a,b in zip(u,c) if a<26000])
"