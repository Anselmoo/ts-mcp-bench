# Edit the solution.py to just print the transitions for Dq=930, B=960
sed -i 's/res = minimize(objective, initial_guess, method=.Nelder-Mead)/print(f"Dq=930, B=960: {calculate_transitions([930, 960])}")/' solution.py
sed -i 's/print(f"Dq: {res.x[0]}, B: {res.x[1]}")//' solution.py
sed -i 's/print(f"Transitions: {calculate_transitions(res.x)}")//' solution.py
python3 solution.py
