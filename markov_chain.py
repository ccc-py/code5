import random

# 轉移矩陣 (Transition Matrix)
#            晴天  雨天
P = [[0.8, 0.2],  # 晴天
     [0.3, 0.7]]  # 雨天

states = ['晴天', '雨天']

def next_state(current):
    """根據轉移矩陣返回下一狀態"""
    idx = 0 if current == '晴天' else 1
    probs = P[idx]
    r = random.random()
    if r < probs[0]:
        return states[0]
    return states[1]

# 模擬 30 天的天氣
current = '晴天'
print(f"起始: {current}")

for day in range(1, 31):
    current = next_state(current)
    print(f"第{day:2d}天: {current}")
