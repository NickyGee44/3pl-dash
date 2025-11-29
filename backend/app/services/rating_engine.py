"""
Rating engine - computes expected charges using tariff data.

Key business rules (from TransX analyst model):
1. Weight breaks: 0-499 (LTL), 500-999, 1000-1999, 2000-4999, 5000-9999, 10000+
2. Use billed weight (PRBWGT) as primary, fallback to scale weight
3. Apply fuel/tax/margin multiplier: base * 1.53
4. MIN charge always applies if linehaul < min
"""
from decimal import Decimal, ROUND_CEILING
from typing import Dict, Optional, Tuple, List

from sqlalchemy.orm import Session

from app.models import Shipment, Tariff
from app.models.tariff import TariffType
from app.services.tariff_cache import TariffLaneCache, get_tariff_cache


# Fuel surcharge (25%) + Tax surcharge (13%) + Margin (15%) = 53%
# Final charge = base * 1.53
FUEL_TAX_MARGIN_MULTIPLIER = Decimal("1.53")

# Standard CWT weight break ranges (in lbs)
# These match the TransX analyst's Excel model
CWT_BREAK_RANGES = [
    (Decimal("0"), Decimal("500"), "LTL"),      # 0-499 lb
    (Decimal("500"), Decimal("1000"), "500"),   # 500-999 lb
    (Decimal("1000"), Decimal("2000"), "1000"), # 1000-1999 lb
    (Decimal("2000"), Decimal("5000"), "2000"), # 2000-4999 lb
    (Decimal("5000"), Decimal("10000"), "5000"), # 5000-9999 lb
    (Decimal("10000"), None, "10000"),          # 10000+ lb
]


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except:
        return None


def _select_billable_weight(weight_value, dim_weight_value) -> Optional[Decimal]:
    """
    Select the billable weight for rating.
    
    Business rule: Use max(scale_weight, billed_weight/dim_weight)
    - dim_weight here represents PRBWGT (billed weight) from the carrier
    - This is the weight the carrier actually charged on
    """
    weight = _to_decimal(weight_value)
    dim_weight = _to_decimal(dim_weight_value)
    candidates = [w for w in [weight, dim_weight] if w and w > 0]
    if not candidates:
        return None
    return max(candidates)


def get_cwt_break_label(weight: Decimal) -> str:
    """
    Determine which CWT break tier a weight falls into.
    
    Returns the break label (e.g., "LTL", "500", "1000", etc.)
    """
    for start, end, label in CWT_BREAK_RANGES:
        if weight >= start:
            if end is None or weight < end:
                return label
    return "10000"  # Fallback to heaviest tier


def rate_cwt_cached(
    billable_weight: Optional[Decimal],
    lane_cache: TariffLaneCache,
    apply_multiplier: bool = True
) -> Optional[Decimal]:
    """
    Rate a shipment using CWT (hundredweight) tariff.
    
    Business rules:
    1. Compute CWT = ceil(weight / 100)
    2. Find the correct weight break tier
    3. linehaul = CWT * rate_per_cwt
    4. base_charge = max(linehaul, min_charge)
    5. final_charge = base_charge * 1.53 (fuel + tax + margin)
    """
    if not billable_weight or billable_weight <= 0:
        return None

    # Compute CWT (hundredweight), rounded up
    cwt = (billable_weight / Decimal("100")).to_integral_value(rounding=ROUND_CEILING)
    
    # Find the correct break based on weight tier
    # The break ranges in tariff_cache should match CWT_BREAK_RANGES
    selected_break = None
    
    for br in lane_cache.cwt_breaks:
        # Check if weight falls within this break's range
        start = br.start or Decimal("0")
        end = br.end
        
        if billable_weight >= start:
            if end is None or billable_weight < end:
                selected_break = br
                break
    
    # If no exact match, try to find the best break
    if not selected_break and lane_cache.cwt_breaks:
        # Sort breaks by start weight and find the appropriate one
        sorted_breaks = sorted(lane_cache.cwt_breaks, key=lambda b: b.start or Decimal("0"))
        
        for br in sorted_breaks:
            start = br.start or Decimal("0")
            end = br.end
            
            if billable_weight >= start:
                if end is None or billable_weight < end:
                    selected_break = br
                    break
                # If weight exceeds this break's end, continue to next
                selected_break = br  # Keep as fallback
    
    if not selected_break:
        return None

    # Calculate linehaul charge
    linehaul = cwt * selected_break.rate_per_cwt
    
    # Apply minimum charge rule
    base_charge = max(linehaul, lane_cache.min_charge)
    
    # Apply fuel/tax/margin multiplier (25% + 13% + 15% = 53%)
    if apply_multiplier:
        final_charge = base_charge * FUEL_TAX_MARGIN_MULTIPLIER
    else:
        final_charge = base_charge
    
    return final_charge.quantize(Decimal("0.01"))


def rate_skid_spot_cached(
    pallets_value,
    weight_value,
    lane_cache: TariffLaneCache,
    apply_multiplier: bool = True
) -> Optional[Decimal]:
    """
    Rate a shipment using skid/spot tariff (e.g., APPS FAK).
    
    Business rules:
    1. Round pallets up to get number of spots
    2. Check weight cap (2000 lb per skid)
    3. Look up spot charge
    4. Apply fuel/tax/margin multiplier
    """
    pallets = _to_decimal(pallets_value) or Decimal("1")
    num_spots = int(pallets.to_integral_value(rounding=ROUND_CEILING))
    num_spots = max(1, num_spots)

    weight = _to_decimal(weight_value)
    # Weight cap: 2000 lb per skid
    if weight and weight > Decimal("2000") * Decimal(num_spots):
        return None

    if not lane_cache.skid_breaks:
        return None

    max_spots = max(lane_cache.skid_breaks.keys())
    spots_to_use = min(num_spots, max_spots)
    base_charge = lane_cache.skid_breaks.get(spots_to_use)
    
    if base_charge is None:
        return None
    
    # Apply fuel/tax/margin multiplier
    if apply_multiplier:
        final_charge = base_charge * FUEL_TAX_MARGIN_MULTIPLIER
    else:
        final_charge = base_charge
    
    return final_charge.quantize(Decimal("0.01"))


def rate_shipment(
    db: Session,
    shipment: Shipment,
    tariff: Tariff
) -> Optional[Decimal]:
    """
    Rate a shipment against a specific tariff.
    
    Returns:
        Expected charge or None if tariff doesn't apply
    """
    cache = get_tariff_cache(db)
    entry = next((e for e in cache.entries if e.id == str(tariff.id)), None)
    if not entry:
        return None
    lane_cache = entry.find_lane(shipment.dest_city, shipment.dest_province)
    if not lane_cache:
        return None
    billable_weight = _select_billable_weight(shipment.weight, shipment.dim_weight)
    if entry.tariff_type == TariffType.CWT:
        return rate_cwt_cached(billable_weight, lane_cache)
    if entry.tariff_type == TariffType.SKID_SPOT:
        return rate_skid_spot_cached(shipment.pallets, shipment.weight, lane_cache)
    return None


def rerate_shipment_all_carriers(
    db: Session,
    shipment: Shipment,
    tariffs: Optional[List[Tariff]] = None
) -> Dict[str, Decimal]:
    """
    Rate a shipment against all applicable tariffs.
    
    Returns:
        Dictionary mapping carrier_name -> expected_charge
    """
    cache = get_tariff_cache(db)
    if tariffs is None:
        entries = cache.entries
    else:
        allowed_ids = {str(tariff.id) for tariff in tariffs}
        entries = [entry for entry in cache.entries if entry.id in allowed_ids]

    results: Dict[str, Decimal] = {}
    origin_dc = shipment.origin_dc.upper().strip() if shipment.origin_dc else None
    billable_weight = _select_billable_weight(shipment.weight, shipment.dim_weight)
    pallets = _to_decimal(shipment.pallets)
    scale_weight = _to_decimal(shipment.weight)

    for entry in entries:
        if origin_dc and entry.origin_dc.upper().strip() != origin_dc:
            continue
        lane_cache = entry.find_lane(shipment.dest_city, shipment.dest_province)
        if not lane_cache:
            continue
        if entry.tariff_type == TariffType.CWT:
            charge = rate_cwt_cached(billable_weight, lane_cache)
        else:
            charge = rate_skid_spot_cached(pallets, scale_weight, lane_cache)
        if charge is not None:
            results[entry.carrier_name] = charge

    return results


def find_best_carrier(charges: Dict[str, Decimal]) -> Tuple[Optional[str], Optional[Decimal]]:
    """
    Find the carrier with the lowest charge.
    
    Returns:
        (carrier_name, best_charge) or (None, None) if empty
    """
    if not charges:
        return (None, None)
    
    best_carrier = min(charges.items(), key=lambda x: x[1])
    return (best_carrier[0], best_carrier[1])

