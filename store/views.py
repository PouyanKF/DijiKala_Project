from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from .models import Product, Category, Store, Cart, CartItem, Transaction, Coupon
from .forms import StoreForm, ProductForm, CouponForm

# ==================== صفحه اصلی ====================
def home_view(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    
   
    main_categories = Category.objects.filter(parent__isnull=True, is_active=True).order_by('order', 'title')
    
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(title__icontains=search_query)
    
    context = {
        'products': products,
        'categories': categories,
        'main_categories': main_categories, 
        'current_category': category_slug,
        'search_query': search_query,
    }
    return render(request, 'home.html', context)


# ==================== جزئیات محصول ====================
def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})


# ==================== سبد خرید ====================
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)
    items = cart.items.all()
    total = cart.total_price
    return render(request, 'cart.html', {'cart_items': items, 'total': total})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.stock < 1:
        messages.error(request, f'متأسفیم! {product.title} موجود نیست.')
        return redirect('store:home')
    
    cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'تعداد {product.title} در سبد خرید افزایش یافت.')
        else:
            messages.warning(request, f'موجودی {product.title} کافی نیست!')
    else:
        messages.success(request, f'{product.title} به سبد خرید اضافه شد.')
    
    return redirect('store:cart')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = item.product.title
    item.delete()
    messages.success(request, f'{product_name} از سبد خرید حذف شد.')
    return redirect('store:cart')


# ==================== پرداخت ====================
@login_required
def payment_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)
    items = cart.items.all()
    
    if not items:
        messages.warning(request, 'سبد خرید شما خالی است!')
        return redirect('store:home')
    
    
    total_price = Decimal(cart.total_price)
    discount = Decimal(request.session.get('discount_amount', 0))
    final_amount = total_price - discount
    if final_amount < 0:
        final_amount = Decimal(0)
    
    available_balance = request.user.available_balance
    wallet_has_enough = available_balance >= final_amount
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # پرداخت با کیف پول
        if payment_method == 'wallet':
            if not wallet_has_enough:
                messages.error(request, 'موجودی کیف پول شما کافی نیست!')
                return render(request, 'payment.html', {
                    'cart': cart,
                    'total': total_price,
                    'final_amount': final_amount,
                    'discount': discount,
                    'success': False,
                    'error': 'موجودی کیف پول کافی نیست! لطفاً روش کارت را انتخاب کنید.',
                    'available_balance': available_balance,
                    'wallet_has_enough': wallet_has_enough,
                })
            
            for item in items:
                if item.product.stock < item.quantity:
                    messages.error(request, f'موجودی {item.product.title} کافی نیست!')
                    return render(request, 'payment.html', {
                        'cart': cart,
                        'total': total_price,
                        'final_amount': final_amount,
                        'discount': discount,
                        'success': False,
                        'error': f'موجودی {item.product.title} کافی نیست.',
                        'available_balance': available_balance,
                        'wallet_has_enough': wallet_has_enough,
                    })
            
            with transaction.atomic():
                request.user.balance -= final_amount
                request.user.save()
                
                Transaction.objects.create(
                    user=request.user,
                    transaction_type='PAYMENT',
                    amount=final_amount,
                    balance_after=request.user.balance,
                    description=f'پرداخت با کیف پول - مبلغ اصلی: {total_price} - تخفیف: {discount} - نهایی: {final_amount}',
                    status='COMPLETED'
                )
                
                for item in items:
                    item.product.stock -= item.quantity
                    item.product.save()
                    
                    item_total = Decimal(item.product.price) * Decimal(item.quantity)
                    ratio = item_total / total_price
                    seller_earning = final_amount * ratio
                    
                    seller = item.product.seller
                    seller.balance += seller_earning
                    seller.save()
                    
                    Transaction.objects.create(
                        user=seller,
                        transaction_type='SELLER_EARNING',
                        amount=seller_earning,
                        balance_after=seller.balance,
                        description=f'درآمد از فروش {item.product.title} (تعداد: {item.quantity}) - سهم از مبلغ نهایی',
                        status='COMPLETED'
                    )
                
                cart.is_paid = True
                coupon_code = request.session.get('coupon_code')
                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        cart.coupon = coupon
                        coupon.used_count += 1
                        coupon.save()
                    except Coupon.DoesNotExist:
                        pass
                
                cart.save()
                
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                if 'discount_amount' in request.session:
                    del request.session['discount_amount']
            
            messages.success(request, f'✅ پرداخت با کیف پول با موفقیت انجام شد! مبلغ: {final_amount} تومان')
            return render(request, 'payment.html', {
                'success': True,
                'total': total_price,
                'final_amount': final_amount,
                'discount': discount,
                'payment_method': 'کیف پول'
            })
        
        # پرداخت با کارت
        else:
            for item in items:
                if item.product.stock < item.quantity:
                    messages.error(request, f'موجودی {item.product.title} کافی نیست!')
                    return render(request, 'payment.html', {
                        'cart': cart,
                        'total': total_price,
                        'final_amount': final_amount,
                        'discount': discount,
                        'success': False,
                        'error': f'موجودی {item.product.title} کافی نیست.',
                        'available_balance': available_balance,
                        'wallet_has_enough': wallet_has_enough,
                    })
            
            card_number = request.POST.get('card_number', '').replace(' ', '')
            if len(card_number) != 16:
                messages.error(request, 'شماره کارت باید ۱۶ رقم باشد.')
                return render(request, 'payment.html', {
                    'cart': cart,
                    'total': total_price,
                    'final_amount': final_amount,
                    'discount': discount,
                    'success': False,
                    'error': 'شماره کارت نامعتبر است!',
                    'available_balance': available_balance,
                    'wallet_has_enough': wallet_has_enough,
                })
            
            with transaction.atomic():
                for item in items:
                    item.product.stock -= item.quantity
                    item.product.save()
                    
                    item_total = Decimal(item.product.price) * Decimal(item.quantity)
                    ratio = item_total / total_price
                    seller_earning = final_amount * ratio
                    
                    seller = item.product.seller
                    seller.balance += seller_earning
                    seller.save()
                    
                    Transaction.objects.create(
                        user=seller,
                        transaction_type='SELLER_EARNING',
                        amount=seller_earning,
                        balance_after=seller.balance,
                        description=f'درآمد از فروش {item.product.title} (تعداد: {item.quantity}) - سهم از مبلغ نهایی',
                        status='COMPLETED'
                    )
                
                cart.is_paid = True
                coupon_code = request.session.get('coupon_code')
                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        cart.coupon = coupon
                        coupon.used_count += 1
                        coupon.save()
                    except Coupon.DoesNotExist:
                        pass
                
                cart.save()
                
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                if 'discount_amount' in request.session:
                    del request.session['discount_amount']
            
            messages.success(request, f'✅ پرداخت با کارت با موفقیت انجام شد! مبلغ: {final_amount} تومان')
            return render(request, 'payment.html', {
                'success': True,
                'total': total_price,
                'final_amount': final_amount,
                'discount': discount,
                'payment_method': 'کارت'
            })
    
    return render(request, 'payment.html', {
        'cart': cart,
        'total': total_price,
        'final_amount': final_amount,
        'discount': discount,
        'success': False,
        'available_balance': available_balance,
        'wallet_has_enough': wallet_has_enough,
    })


# ==================== سایر توابع ====================
@login_required
def checkout(request):
    return redirect('store:payment')


@login_required
def seller_panel_view(request):
    if request.user.role != 'SELLER' and not request.user.is_superuser:
        messages.warning(request, 'شما دسترسی به این صفحه را ندارید.')
        return redirect('store:home')
    stores = Store.objects.filter(owner=request.user)
    total_products = Product.objects.filter(seller=request.user).count()
    return render(request, 'seller_panel.html', {'stores': stores, 'total_products': total_products})


@login_required
def create_store(request):
    if request.user.role != 'SELLER':
        messages.warning(request, 'فقط فروشندگان می‌توانند فروشگاه ایجاد کنند.')
        return redirect('store:home')
    if request.method == 'POST':
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.save()
            messages.success(request, f'فروشگاه "{store.name}" با موفقیت ایجاد شد!')
            return redirect('store:seller_panel')
    else:
        form = StoreForm()
    return render(request, 'create_store.html', {'form': form})


@login_required
def add_product_view(request):
    if request.user.role != 'SELLER':
        messages.warning(request, 'فقط فروشندگان می‌توانند محصول اضافه کنند.')
        return redirect('store:home')
    stores = Store.objects.filter(owner=request.user)
    if not stores:
        messages.warning(request, 'ابتدا یک فروشگاه ایجاد کنید!')
        return redirect('store:create_store')
    categories = Category.objects.all()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            store_id = request.POST.get('store')
            if store_id:
                store = get_object_or_404(Store, id=store_id, owner=request.user)
                product.store = store
            else:
                messages.error(request, 'لطفاً فروشگاه را انتخاب کنید.')
                return render(request, 'add_product.html', {
                    'form': form,
                    'stores': stores,
                    'categories': categories
                })
            product.seller = request.user
            product.save()
            messages.success(request, f'محصول "{product.title}" با موفقیت اضافه شد!')
            return redirect('store:seller_panel')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {
        'form': form,
        'stores': stores,
        'categories': categories
    })


@login_required
def delete_product_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.user.is_superuser or request.user.role == 'ADMIN' or product.seller == request.user:
        product.delete()
        messages.success(request, 'محصول با موفقیت حذف شد.')
    else:
        messages.error(request, 'شما مجاز به حذف این محصول نیستید!')
    return redirect('store:home')


@login_required
def customer_panel_view(request):
    return render(request, 'customer_panel.html')


# ==================== کیف پول ====================
@login_required
def wallet_view(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    context = {
        'user': request.user,
        'transactions': transactions,
        'available_balance': request.user.available_balance,
    }
    return render(request, 'wallet.html', context)


@login_required
def wallet_deposit(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'مبلغ باید بزرگتر از صفر باشد.')
                return redirect('store:wallet')
            with transaction.atomic():
                request.user.balance += amount
                request.user.save()
                Transaction.objects.create(
                    user=request.user,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    balance_after=request.user.balance,
                    description=f'شارژ کیف پول به مبلغ {amount} تومان',
                    status='COMPLETED',
                    reference_id=f'DEP-{request.user.id}-{amount}'
                )
            messages.success(request, f'کیف پول شما به مبلغ {amount} تومان شارژ شد.')
        except ValueError:
            messages.error(request, 'مبلغ وارد شده معتبر نیست.')
        except Exception as e:
            messages.error(request, f'خطا در شارژ کیف پول: {str(e)}')
        return redirect('store:wallet')
    return redirect('store:wallet')


@login_required
def seller_withdraw(request):
    if request.user.role != 'SELLER' and not request.user.is_superuser:
        messages.error(request, 'فقط فروشندگان می‌توانند برداشت کنند.')
        return redirect('store:home')
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'مبلغ باید بزرگتر از صفر باشد.')
                return redirect('store:wallet')
            if amount > request.user.available_balance:
                messages.error(request, 'موجودی کافی نیست.')
                return redirect('store:wallet')
            with transaction.atomic():
                request.user.balance -= amount
                request.user.save()
                Transaction.objects.create(
                    user=request.user,
                    transaction_type='SELLER_WITHDRAW',
                    amount=amount,
                    balance_after=request.user.balance,
                    description=f'برداشت از کیف پول به مبلغ {amount} تومان',
                    status='COMPLETED',
                    reference_id=f'WTH-{request.user.id}-{amount}'
                )
            messages.success(request, f'برداشت به مبلغ {amount} تومان با موفقیت انجام شد.')
        except ValueError:
            messages.error(request, 'مبلغ وارد شده معتبر نیست.')
        except Exception as e:
            messages.error(request, f'خطا در برداشت: {str(e)}')
        return redirect('store:wallet')
    return redirect('store:wallet')


@login_required
def wallet_transactions(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    context = {
        'transactions': transactions,
        'user': request.user,
        'available_balance': request.user.available_balance,
        'filter_type': transaction_type,
    }
    return render(request, 'wallet_transactions.html', context)
# ===== مدیریت کدهای تخفیف =====
@login_required
def coupon_list(request):
    if request.user.role != 'SELLER' and not request.user.is_superuser:
        messages.error(request, 'شما دسترسی به این صفحه را ندارید.')
        return redirect('store:home')
    coupons = Coupon.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'coupon_list.html', {'coupons': coupons})


@login_required
def coupon_create(request):
    if request.user.role != 'SELLER' and not request.user.is_superuser:
        messages.error(request, 'شما دسترسی به این صفحه را ندارید.')
        return redirect('store:home')
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.created_by = request.user
            coupon.save()
            form.save_m2m()
            messages.success(request, f'کد تخفیف "{coupon.code}" با موفقیت ایجاد شد!')
            return redirect('store:coupon_list')
    else:
        form = CouponForm()
    return render(request, 'coupon_create.html', {'form': form, 'title': 'ایجاد کد تخفیف جدید'})


@login_required
def coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if coupon.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه ویرایش این کد را ندارید.')
        return redirect('store:coupon_list')
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f'کد تخفیف "{coupon.code}" با موفقیت ویرایش شد!')
            return redirect('store:coupon_list')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'coupon_create.html', {'form': form, 'coupon': coupon, 'title': 'ویرایش کد تخفیف'})


@login_required
def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if coupon.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه حذف این کد را ندارید.')
        return redirect('store:coupon_list')
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, 'کد تخفیف با موفقیت حذف شد.')
        return redirect('store:coupon_list')
    return render(request, 'coupon_delete.html', {'coupon': coupon})


@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip().upper()
        cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)
        total_price = cart.total_price
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
            if not coupon.is_valid:
                return JsonResponse({'success': False, 'error': 'کد تخفیف منقضی شده یا نامعتبر است.'}, status=400)
            if total_price < coupon.min_order_amount:
                return JsonResponse({'success': False, 'error': f'حداقل مبلغ سفارش برای این کد {coupon.min_order_amount} تومان است.'}, status=400)
            if not coupon.can_use_by_user(request.user):
                return JsonResponse({'success': False, 'error': 'شما قبلاً از این کد تخفیف استفاده کرده‌اید.'}, status=400)
            discount_amount = coupon.apply_discount(total_price)
            request.session['coupon_code'] = code
            request.session['discount_amount'] = int(discount_amount)
            return JsonResponse({
                'success': True,
                'discount_amount': int(discount_amount),
                'final_amount': int(total_price - discount_amount),
                'coupon_code': code
            })
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'کد تخفیف نامعتبر است.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'}, status=400)


@login_required
def remove_coupon(request):
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    if 'discount_amount' in request.session:
        del request.session['discount_amount']
    return JsonResponse({'success': True})
# ===== مدیریت محصولات فروشنده =====
@login_required
def seller_products(request):
    if request.user.role != 'SELLER' and not request.user.is_superuser:
        messages.error(request, 'شما دسترسی به این صفحه را ندارید.')
        return redirect('store:home')
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(title__icontains=search_query)
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    stock_filter = request.GET.get('stock')
    if stock_filter == 'in_stock':
        products = products.filter(stock__gt=0)
    elif stock_filter == 'out_of_stock':
        products = products.filter(stock=0)
    categories = Category.objects.all()
    total_products = products.count()
    total_stock = sum(p.stock for p in products)
    avg_price = sum(p.price for p in products) / total_products if total_products > 0 else 0
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'stock_filter': stock_filter,
        'total_products': total_products,
        'total_stock': total_stock,
        'avg_price': avg_price,
    }
    return render(request, 'seller_products.html', context)


@login_required
def seller_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.seller != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه ویرایش این محصول را ندارید.')
        return redirect('store:seller_products')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'محصول "{product.title}" با موفقیت ویرایش شد!')
            return redirect('store:seller_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'seller_product_edit.html', {'form': form, 'product': product, 'title': 'ویرایش محصول'})


@login_required
def seller_product_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.seller != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه تغییر موجودی این محصول را ندارید.')
        return redirect('store:seller_products')
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 0))
            action = request.POST.get('action')
            if quantity <= 0:
                messages.error(request, 'تعداد باید بزرگتر از صفر باشد.')
                return redirect('store:seller_product_stock', pk=product.pk)
            if action == 'increase':
                product.stock += quantity
                product.save()
                messages.success(request, f'موجودی "{product.title}" به {product.stock} افزایش یافت.')
            elif action == 'decrease':
                if product.stock >= quantity:
                    product.stock -= quantity
                    product.save()
                    messages.success(request, f'موجودی "{product.title}" به {product.stock} کاهش یافت.')
                else:
                    messages.error(request, f'موجودی کافی نیست! موجودی فعلی: {product.stock}')
            else:
                messages.error(request, 'عملیات نامعتبر.')
        except ValueError:
            messages.error(request, 'تعداد باید عدد باشد.')
        return redirect('store:seller_products')
    return render(request, 'seller_product_stock.html', {'product': product, 'title': 'تغییر موجودی'})


@login_required
def seller_product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.seller != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه این کار را ندارید.')
        return redirect('store:seller_products')
    if hasattr(product, 'is_active'):
        product.is_active = not product.is_active
        product.save()
        status = 'فعال' if product.is_active else 'غیرفعال'
        messages.success(request, f'وضعیت محصول "{product.title}" به {status} تغییر یافت.')
    else:
        messages.warning(request, 'فیلد is_active در مدل Product وجود ندارد.')
    return redirect('store:seller_products')


@login_required
def seller_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.seller != request.user and not request.user.is_superuser:
        messages.error(request, 'شما اجازه حذف این محصول را ندارید.')
        return redirect('store:seller_products')
    if request.method == 'POST':
        product_title = product.title
        product.delete()
        messages.success(request, f'محصول "{product_title}" با موفقیت حذف شد.')
        return redirect('store:seller_products')
    return render(request, 'seller_product_delete.html', {'product': product})