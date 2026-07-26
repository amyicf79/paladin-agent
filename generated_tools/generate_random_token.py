import random, string
def generate_random_token(length=16):
    """生成指定长度的随机令牌"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
