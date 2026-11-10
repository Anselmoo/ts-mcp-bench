
cd /tmp/tsbench-run-711ytt10/w && sed -i 's/    print(sol.x, res(sol.x))/    print("SOL", sol.x, res(sol.x))/' fit2.py && python3 fit2.py 2>&1 | grep -E "SOL|^\(" 