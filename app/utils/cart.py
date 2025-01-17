from typing import List
from app.models.cart import CartBase, CartItemResponse, CartResponse
from app.models.product import ProductBase


def build_cart_response(cart: CartBase, products: List[ProductBase]) -> CartResponse:
    product_map = {str(p.id): p for p in products}
    cart_items = []
    for item in cart.items:
        product = product_map.get(item.product_id)
        if product:
            cart_items.append(
                CartItemResponse(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    name=product.name,
                    price=product.price,
                    image=product.images[0] if product.images else None,
                    stock=product.stock,
                )
            )

    return CartResponse(
        user_id=cart.user_id, items=cart_items, updated_at=cart.updated_at
    )
