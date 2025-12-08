from django import template

register = template.Library()


@register.filter
def sum_pieces(inventories):
    """Sum all quantity_pieces from inventories"""
    if not inventories:
        return 0
    return sum(inv.quantity_pieces for inv in inventories)


@register.filter
def sum_board_feet(inventories):
    """Sum all total_board_feet from inventories"""
    if not inventories:
        return 0
    return sum(float(inv.total_board_feet) for inv in inventories)


@register.filter
def sum_pieces_moved(transactions):
    """Sum all quantity_pieces from transactions"""
    if not transactions:
        return 0
    return sum(tx.quantity_pieces for tx in transactions)


@register.filter
def sum_board_feet_moved(transactions):
    """Sum all board_feet from transactions"""
    if not transactions:
        return 0
    return sum(float(tx.board_feet) for tx in transactions)
