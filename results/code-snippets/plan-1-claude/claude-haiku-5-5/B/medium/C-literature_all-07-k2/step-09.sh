
cd /tmp/tsbench-run-ub74fb61 && sed -i 's/hR=np.diag(\[-4\*Dq,-4\*Dq,-4\*Dq,6\*Dq,6\*Dq\])/hR=np.diag([-4*Dq,6*Dq,-4*Dq,-4*Dq,6*Dq])/' d5.py && grep -n "hR=" d5.py && timeout 900 python3 fit.py
