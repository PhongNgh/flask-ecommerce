from flask import jsonify, render_template, flash, redirect, url_for, session, request
from flask_jwt_extended import get_jwt_identity, get_jwt
from app import mongo
from bson import ObjectId
from datetime import datetime, timedelta
import random
import string

def generate_order_id():
    """Tạo mã đơn hàng với định dạng DH + 15 ký tự số ngẫu nhiên."""
    prefix = "DH"
    random_digits = ''.join(random.choices(string.digits, k=15))
    return prefix + random_digits

def apply_voucher(voucher_code, subtotal):
    """Kiểm tra và áp dụng voucher."""
    try:
        voucher = mongo.db.vouchers.find_one({"code": voucher_code})
        if not voucher:
            return None, "Mã voucher không hợp lệ!"
        if voucher["quantity"] <= 0:
            return None, "Mã voucher đã hết lượt sử dụng!"
        if datetime.strptime(voucher["expiry_date"], '%Y-%m-%d') < datetime.now():
            return None, "Mã voucher đã hết hạn!"
        
        discount_percent = float(voucher["discount"])
        discount_amount = subtotal * (discount_percent / 100)
        return discount_amount, f"Áp dụng voucher thành công!"
    except Exception as e:
        return None, f"Lỗi khi áp dụng voucher: {str(e)}"
    
def apply_voucher_exc():
    """Xử lý AJAX request để áp dụng voucher."""
    try:
        data = request.get_json()
        voucher_code = data.get('voucher_code')
        subtotal = float(data.get('subtotal'))

        discount_amount, message = apply_voucher(voucher_code, subtotal)
        if discount_amount:
            new_total = subtotal - discount_amount
            return jsonify({
                "success": True,
                "message": message,
                "discount_amount": discount_amount,
                "new_total": new_total
            })
        return jsonify({"success": False, "error": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def checkout_exc():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            flash("Vui lòng đăng nhập để tiếp tục thanh toán.", "danger")
            return redirect(url_for('login'))

        claims = get_jwt()
        discount_amount = claims.get('discount_amount', 0)

        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        if not cart or 'products' not in cart:
            flash("Giỏ hàng của bạn đang trống.", "warning")
            return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)

        product_ids = [item['product_id'] for item in cart['products']]
        valid_product_ids = []
        for pid in product_ids:
            try:
                valid_product_ids.append(ObjectId(pid))
            except:
                continue

        products = mongo.db.products.find({"_id": {"$in": valid_product_ids}})
        products_list = list(products)

        cart_items = []
        subtotal = 0
        for product in products_list:
            product['_id'] = str(product['_id'])
            for item in cart['products']:
                if str(item['product_id']) == product['_id']:
                    product['quantity'] = item['quantity']
                    price = float(product['price']) if isinstance(product['price'], (str, int)) else product['price']
                    subtotal += price * item['quantity']
                    cart_items.append(product)
                    break

        if not cart_items:
            flash("Không có sản phẩm hợp lệ trong giỏ hàng.", "warning")
            return redirect(url_for('cart'))

        # Áp dụng voucher nếu có
        voucher_code = request.args.get('voucher_code') or session.get('voucher_code')
        voucher_discount = 0
        if voucher_code:
            discount_amount, message = apply_voucher(voucher_code, subtotal)
            if discount_amount:
                voucher_discount = discount_amount
                session['voucher_code'] = voucher_code
                session['voucher_discount'] = voucher_discount
            else:
                session.pop('voucher_code', None)
                session.pop('voucher_discount', None)

        total = subtotal - (float(discount_amount) + voucher_discount)

        addresses = list(mongo.db.list_address.find({"user_id": ObjectId(user_id)}))
        for address in addresses:
            address['_id'] = str(address['_id'])
            address['user_id'] = str(address['user_id'])

        default_address = next((addr for addr in addresses if addr.get('is_default', False)), None)

        if request.method == 'POST':
            receiver_name = request.form.get('receiverName')
            email = request.form.get('email')
            payment_method = request.form.get('paymentMethod')

            if not receiver_name or not email or not payment_method:
                flash("Vui lòng điền đầy đủ thông tin.", "danger")
                return redirect(url_for('checkout'))

            selected_address_id = request.form.get('selected_address')
            if selected_address_id:
                selected_address = next((addr for addr in addresses if addr['_id'] == selected_address_id), None)
                if not selected_address:
                    flash("Địa chỉ không hợp lệ.", "danger")
                    return redirect(url_for('checkout'))
                address = selected_address['street']
                phone = selected_address['phone']
            else:
                address = request.form.get('address')
                phone = request.form.get('phone')
                address_type = request.form.get('addressType')
                set_default = request.form.get('setDefault') == 'on'

                if not address or not phone or not address_type:
                    flash("Vui lòng điền đầy đủ thông tin địa chỉ.", "danger")
                    return redirect(url_for('checkout'))

                if address_type not in ["Nhà riêng", "Văn phòng"]:
                    flash("Loại địa chỉ không hợp lệ.", "danger")
                    return redirect(url_for('checkout'))

                new_address = {
                    "user_id": ObjectId(user_id),
                    "name": address_type,
                    "street": address,
                    "phone": phone,
                    "is_default": set_default
                }
                if set_default:
                    mongo.db.list_address.update_many(
                        {"user_id": ObjectId(user_id), "is_default": True},
                        {"$set": {"is_default": False}}
                    )
                mongo.db.list_address.insert_one(new_address)

            for item in cart['products']:
                product_id = item['product_id']
                quantity_ordered = item['quantity']
                product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
                if product and 'quantity' in product:
                    current_quantity = product['quantity']
                    if current_quantity >= quantity_ordered:
                        new_quantity = current_quantity - quantity_ordered
                        mongo.db.products.update_one(
                            {"_id": ObjectId(product_id)},
                            {"$set": {"quantity": new_quantity}}
                        )
                    else:
                        flash(f"Sản phẩm {product['name']} không đủ số lượng để đặt hàng.", "danger")
                        return redirect(url_for('checkout'))

            order = {
                "order_id": generate_order_id(),
                "user_id": ObjectId(user_id),
                "receiver_name": receiver_name,
                "receiver_phone": phone,
                "receiver_email": email,
                "receiver_address": address,
                "payment_method": payment_method,
                "items": cart_items,
                "subtotal": subtotal,
                "discount": float(discount_amount) + voucher_discount,
                "total": total,
                "order_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "payment_status": "pending",
                "delivery_status": "pending",
                "voucher_code": voucher_code if voucher_code else None
            }

            if voucher_code:
                mongo.db.vouchers.update_one(
                    {"code": voucher_code},
                    {"$inc": {"quantity": -1}}
                )

            mongo.db.orders.insert_one(order)
            mongo.db.carts.delete_one({"user_id": ObjectId(user_id)})
            session.pop('voucher_code', None)
            session.pop('voucher_discount', None)

            if payment_method == "COD":
                return render_template('cart/order-complete.html', order=order)
            else:
                session['pending_order'] = order
                return redirect(url_for('payments'))

        return render_template('cart/checkout.html', cart_items=cart_items, subtotal=subtotal, total=total, addresses=addresses, default_address=default_address)

    except Exception as e:
        print(f"Error in checkout_exc: {str(e)}")
        flash(f"Đã xảy ra lỗi: {str(e)}", "danger")
        return render_template('cart/checkout.html', cart_items=[], subtotal=0, total=0, addresses=[], default_address=None)

def payments_exc():
    """Hiển thị trang thanh toán cho Chuyển khoản ngân hàng hoặc VNPAY."""
    order = session.get('pending_order')
    if not order:
        flash("Không tìm thấy thông tin đơn hàng.", "danger")
        return redirect(url_for('checkout'))
    return render_template('cart/payments.html', order=order)

def invoice_detail_exc(order_id):
    # Lấy user_id từ JWT
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for('login'))

    # Tìm đơn hàng trong database
    order = mongo.db.orders.find_one({"order_id": order_id, "user_id": ObjectId(user_id)})
    if not order:
        flash("Không tìm thấy đơn hàng.", "danger")
        return redirect(url_for('orders'))

    # Chuyển đổi ObjectId thành string
    order['_id'] = str(order['_id'])
    order['user_id'] = str(order['user_id'])

    # Kiểm tra và đảm bảo order['items'] là danh sách
    if 'items' not in order or not isinstance(order['items'], list):
        print(f"Invalid items data for order {order_id}: {order.get('items')}")
        order['items'] = []  # Gán mặc định là danh sách rỗng để tránh lỗi

    return render_template('cart/invoice-detail.html', order=order)