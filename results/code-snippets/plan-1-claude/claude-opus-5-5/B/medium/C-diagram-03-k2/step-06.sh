
cd /tmp/tsbench-run-tsr9v_05 && sed -i "s/if od\*mult!=deg: lab='?%d'%deg/if od*mult!=deg or od not in (1,2,3): lab='?%d_%d_%.4f'%(deg,mult,chi)/" ts.py && python ts.py 2>&1 | tail -12