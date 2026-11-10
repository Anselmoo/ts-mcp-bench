sed -i "s/bounds=((1, 2000), (1, 10000))/bounds=([1, 1], [2000, 10000])/" solver.py
python3 solver.py
