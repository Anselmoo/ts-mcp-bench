def solve():
    nu1 = 16611
    nu2 = 23529
    c_over_b = 4.5
    
    # Assuming nu2 - nu1 = 16*B
    B = (nu2 - nu1) / 16
    C = c_over_b * B
    
    # Using nu1 = 10*Dq - 4*B + 2*C
    # nu1 = 10*Dq - 4*B + 2*(4.5*B) = 10*Dq + 5*B
    Dq = (nu1 - 5 * B) / 10
    
    print(f"B = {B}")
    print(f"C = {C}")
    print(f"Dq = {Dq}")

solve()
