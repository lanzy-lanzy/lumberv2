from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib import messages

from .models import (
    RoundWoodPurchase,
    RoundWoodInventory,
    WoodType,
)
from app_supplier.models import Supplier


@login_required
def round_wood_dashboard(request):
    """Round Wood Purchasing Dashboard - SIMPLIFIED"""

    purchases = RoundWoodPurchase.objects.select_related("supplier", "wood_type")

    # Summary statistics
    summary = {
        "total_purchases": purchases.count(),
        "total_volume": purchases.filter(status="completed").aggregate(
            Sum("volume_cubic_feet")
        )["volume_cubic_feet__sum"]
        or 0,
        "total_spent": purchases.filter(status="completed").aggregate(
            Sum("total_cost")
        )["total_cost__sum"]
        or 0,
        "pending": purchases.filter(status="pending").count(),
        "completed": purchases.filter(status="completed").count(),
    }

    # Recent purchases
    recent_purchases = purchases.order_by("-purchase_date")[:5]

    # Inventory summary
    inventory_summary = RoundWoodInventory.objects.aggregate(
        total_logs=Sum("total_logs_in_stock"),
        total_volume=Sum("total_cubic_feet_in_stock"),
        total_cost=Sum("total_cost_invested"),
    )

    context = {
        "summary": summary,
        "recent_purchases": recent_purchases,
        "inventory_summary": inventory_summary,
    }

    return render(request, "round_wood/dashboard.html", context)


@login_required
def purchase_list(request):
    """List all round wood purchases"""
    queryset = RoundWoodPurchase.objects.select_related("supplier", "wood_type")

    # Filters
    supplier = request.GET.get("supplier")
    wood_type = request.GET.get("wood_type")
    search = request.GET.get("search")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if supplier:
        queryset = queryset.filter(supplier_id=supplier)
    if wood_type:
        queryset = queryset.filter(wood_type_id=wood_type)
    if date_from:
        queryset = queryset.filter(purchase_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(purchase_date__lte=date_to)
    if search:
        queryset = queryset.filter(
            Q(supplier__company_name__icontains=search)
            | Q(wood_type__name__icontains=search)
            | Q(notes__icontains=search)
        )

    # Sorting
    sort = request.GET.get("sort", "-purchase_date")
    if sort == "-purchase_date":
        queryset = queryset.order_by("-purchase_date", "-id")
    else:
        queryset = queryset.order_by(sort)

    # Calculate summary totals for the filtered queryset
    summary = queryset.aggregate(
        logs=Sum("quantity_logs"),
        board_feet=Sum("board_feet"),
        cost=Sum("total_cost"),
    )

    # Pagination
    page = int(request.GET.get("page", 1))
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page

    total = queryset.count()
    purchases = queryset[start:end]

    # Get filters for dropdowns
    suppliers = Supplier.objects.all()
    wood_types = WoodType.objects.filter(is_active=True)

    context = {
        "purchases": purchases,
        "suppliers": suppliers,
        "wood_types": wood_types,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "summary": {
            "logs": summary["logs"] or 0,
            "board_feet": summary["board_feet"] or 0,
            "cost": summary["cost"] or 0,
        },
        "current_filters": {
            "supplier": supplier,
            "wood_type": wood_type,
            "search": search,
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    return render(request, "round_wood/purchase_list.html", context)


@login_required
def purchase_create(request):
    """Create a new round wood purchase - with board feet calculation"""
    if request.method == "POST":
        try:
            supplier_id = request.POST.get("supplier_id")
            wood_type_id = request.POST.get("wood_type_id")
            quantity_logs = int(request.POST.get("quantity_logs"))
            purchase_date = request.POST.get("purchase_date")
            notes = request.POST.get("notes", "")

            # Board feet calculation fields
            length_inches = float(request.POST.get("length_inches", 0) or 0)
            width_inches = float(request.POST.get("width_inches", 0) or 0)
            thickness_inches = float(request.POST.get("thickness_inches", 0) or 0)

            # Price per board feet
            unit_cost_board_feet = float(request.POST.get("unit_cost_per_board_feet"))

            supplier = Supplier.objects.get(id=supplier_id)
            wood_type = WoodType.objects.get(id=wood_type_id)

            # Create purchase record - saved directly as completed
            purchase = RoundWoodPurchase.objects.create(
                supplier=supplier,
                wood_type=wood_type,
                quantity_logs=quantity_logs,
                length_inches=length_inches,
                width_inches=width_inches,
                thickness_inches=thickness_inches,
                unit_cost_per_board_feet=unit_cost_board_feet,
                purchase_date=purchase_date or timezone.now().date(),
                notes=notes,
                created_by=request.user,
                status="completed",
            )

            messages.success(request, f"Round wood purchase recorded successfully")
            return redirect("round_wood:purchase_detail", pk=purchase.id)

        except Exception as e:
            messages.error(request, f"Error creating purchase: {str(e)}")

    suppliers = Supplier.objects.all()
    wood_types = WoodType.objects.filter(is_active=True)
    today = timezone.now().date()

    context = {"suppliers": suppliers, "wood_types": wood_types, "today": today}
    return render(request, "round_wood/purchase_create.html", context)


@login_required
def purchase_detail(request, pk):
    """View round wood purchase details"""
    purchase = get_object_or_404(RoundWoodPurchase, pk=pk)

    context = {
        "purchase": purchase,
    }

    return render(request, "round_wood/purchase_detail.html", context)


@login_required
@require_http_methods(["POST"])
def purchase_action(request, pk, action):
    """Handle purchase actions"""
    purchase = get_object_or_404(RoundWoodPurchase, pk=pk)

    try:
        if action == "complete":
            if purchase.status == "completed":
                messages.error(request, "Purchase is already completed")
                return redirect("round_wood:purchase_detail", pk=pk)

            purchase.mark_completed()
            messages.success(
                request, "Purchase marked as completed and inventory updated"
            )

        elif action == "cancel":
            if purchase.status == "completed":
                messages.error(request, "Cannot cancel completed purchases")
                return redirect("round_wood:purchase_detail", pk=pk)

            purchase.status = "cancelled"
            purchase.save()
            messages.info(request, "Purchase cancelled")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    return redirect("round_wood:purchase_detail", pk=pk)


@login_required
def inventory_list(request):
    """View inventory levels"""
    inventory = RoundWoodInventory.objects.select_related("wood_type").order_by(
        "wood_type__name"
    )

    # Summary
    summary = RoundWoodInventory.objects.aggregate(
        total_logs=Sum("total_logs_in_stock"),
        total_volume=Sum("total_cubic_feet_in_stock"),
        total_cost=Sum("total_cost_invested"),
    )

    context = {
        "inventory": inventory,
        "summary": summary,
    }

    return render(request, "round_wood/inventory_list.html", context)


@login_required
def wood_types_list(request):
    """Manage wood types"""
    wood_types = WoodType.objects.all().order_by("name")

    context = {
        "wood_types": wood_types,
    }

    return render(request, "round_wood/wood_types_list.html", context)


@login_required
@require_http_methods(["POST"])
def create_walkin_supplier(request):
    """Create a new walk-in supplier for round wood purchase"""
    try:
        company_name = request.POST.get("company_name", "").strip()
        contact_person = request.POST.get("contact_person", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        # Validation
        if not company_name:
            return JsonResponse({"message": "Company name is required"}, status=400)
        if not contact_person:
            return JsonResponse({"message": "Contact person is required"}, status=400)
        if not phone_number:
            return JsonResponse({"message": "Phone number is required"}, status=400)

        # Create supplier
        supplier = Supplier.objects.create(
            company_name=company_name,
            contact_person=contact_person,
            phone_number=phone_number,
            email=email or "",
            address=address or "",
            is_active=True,
        )

        return JsonResponse(
            {
                "id": supplier.id,
                "company_name": supplier.company_name,
                "contact_person": supplier.contact_person,
                "phone_number": supplier.phone_number,
            },
            status=201,
        )

    except Exception as e:
        return JsonResponse(
            {"message": f"Error creating supplier: {str(e)}"}, status=500
        )


@login_required
@require_http_methods(["POST"])
def create_wood_type(request):
    """Create a new wood type for round wood purchase"""
    try:
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        # Validation
        if not name:
            return JsonResponse({"message": "Wood type name is required"}, status=400)

        # Check if wood type already exists
        if WoodType.objects.filter(name__iexact=name).exists():
            return JsonResponse(
                {"message": "This wood type already exists"}, status=400
            )

        # Create wood type
        wood_type = WoodType.objects.create(
            name=name,
            description=description or "",
            is_active=True,
        )

        return JsonResponse(
            {
                "id": wood_type.id,
                "name": wood_type.name,
                "description": wood_type.description,
            },
            status=201,
        )

    except Exception as e:
        return JsonResponse(
            {"message": f"Error creating wood type: {str(e)}"}, status=500
        )
