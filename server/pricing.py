"""Shared pricing policy for CLI estimates and HTTP bookings."""


def quote(price, people):
    if not isinstance(people, int) or isinstance(people, bool) or not 1 <= people <= 8:
        raise ValueError('同行人数需要在 1–8 人之间')
    return price + max(0, people - 4) * 60
