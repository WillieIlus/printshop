# quotes/services.py

import math
from decimal import Decimal
from django.db.models import Q

from inventory.models import MaterialStock
from pricing.models import DigitalPrintPrice, FinishingPrice, PricingTier, MaterialPrice

class QuoteCalculator:
    """
    Service class to calculate costs for QuoteItems and their Parts.
    """

    @staticmethod
    def calculate_imposition(part_width: Decimal, part_height: Decimal, stock_width: Decimal, stock_height: Decimal) -> int:
        """
        Calculates how many cut-items fit on a stock sheet (N-Up).
        Tries both orientations (Portrait vs Landscape).
        Does not account for bleeds/gutters in this simplified version.
        """
        # Convert to float for floor division logic, then int
        pw, ph = float(part_width), float(part_height)
        sw, sh = float(stock_width), float(stock_height)

        if pw > sw and pw > sh: return 0 # Too big to fit
        if ph > sw and ph > sh: return 0 

        # Option A: Standard Orientation
        col_a = int(sw // pw)
        row_a = int(sh // ph)
        count_a = col_a * row_a

        # Option B: Rotated Orientation
        col_b = int(sw // ph)
        row_b = int(sh // pw)
        count_b = col_b * row_b

        return max(count_a, count_b)

    def calculate_part_cost(self, part) -> Decimal:
        """
        Calculates the cost of a single Part (e.g. Inner Pages) considering:
        1. Material Cost (based on sheets used).
        2. Print Cost (Simplex vs Custom Duplex Rate).
        Updates the 'part' model instance with calculation results but does NOT save it.
        """
        # 1. Determine Stock Size
        # If preferred stock not set, find the 'Sheet' stock for this material
        stock = part.preferred_stock
        if not stock:
            # Simple logic: grab the first available stock variant for this material
            stock = part.material.stock_variants.first()
            if not stock:
                raise ValueError(f"No stock defined for material {part.material.name}")

        # 2. Imposition
        items_per_sheet = self.calculate_imposition(
            part.final_width, part.final_height, stock.width, stock.height
        )
        
        if items_per_sheet == 0:
            raise ValueError(f"Part {part.name} ({part.final_width}x{part.final_height}) is too big for stock {stock.label}")

        part.items_per_sheet = items_per_sheet

        # 3. Calculate Sheets Required
        # Total items needed = Quote Quantity. 
        # Note: If it's a book, quantity is books. If this part is "Inner Pages" and a book has 50 pages...
        # The 'QuoteItemPart' doesn't currently store "pages per book". 
        # ASSUMPTION: For this context, we assume the 'part' represents the total run or the model 
        # is mapped 1-to-1. If this is a 50-page book, strictly speaking, 
        # the part logic needs to know "50 pages per unit". 
        # For simplicity of this SaaS MVP, we assume QuoteItem.quantity * 1 unless extended.
        
        total_items_needed = part.item.quantity 
        
        # Ceil division to get full sheets
        sheets_required = math.ceil(total_items_needed / items_per_sheet)
        part.total_sheets_required = sheets_required

        # 4. GET MATERIAL PRICE
        try:
            mat_price_obj = MaterialPrice.objects.get(
                shop=part.item.quote.shop, 
                material=part.material
            )
            material_cost = sheets_required * mat_price_obj.calculated_selling_price
        except MaterialPrice.DoesNotExist:
            material_cost = Decimal("0.00") # Or raise error

        # 5. GET PRINT PRICE
        # We need to match Machine + Stock Label (e.g. SRA3).
        # DigitalPrintPrice maps to SheetSize Enum. We need to normalize stock label to Enum if possible, 
        # or assume the MachinePrintPrice.sheet_size matches the stock.label roughly.
        # For robustness, we query strictly on shop/machine and filter in python or exact match if labels align.
        
        # Try to find a print price for this machine and stock size (e.g., SRA3)
        try:
            print_price_obj = DigitalPrintPrice.objects.get(
                shop=part.item.quote.shop,
                machine=part.machine,
                sheet_size__iexact=stock.label # Assuming label matches Enum 'SRA3'
            )
            
            # 6. CALCULATE PRINTING COST (The "Smart Pricing" logic)
            # Logic: If Simplex, click_rate. If Duplex, duplex_rate.
            if part.print_sides == 'DUPLEX':
                if print_price_obj.duplex_rate:
                    rate = print_price_obj.duplex_rate # Use the specific override (e.g. 25)
                else:
                    rate = print_price_obj.click_rate * 2 # Default doubling (e.g. 15 * 2 = 30)
            else:
                rate = print_price_obj.click_rate # Simplex (e.g. 15)

            # Apply Min Order Quantity logic from pricing model
            billable_sheets = max(sheets_required, print_price_obj.minimum_order_quantity)
            print_cost = billable_sheets * rate

        except DigitalPrintPrice.DoesNotExist:
            # Fallback or Error
            print_cost = Decimal("0.00") 

        total_part_cost = material_cost + print_cost
        part.part_cost = total_part_cost
        return total_part_cost

    def calculate_finishing_cost(self, finishing_item, total_sheets_in_item, total_quote_qty) -> Decimal:
        """
        Calculates cost for a specific finishing service attached to an item.
        Handles: Per Sheet, Per Unit, Per Job, Bulk Tiers.
        """
        price_config = finishing_item.finishing_price
        shop = price_config.shop
        
        # 1. Determine Base Rate (Check for Bulk Tiers)
        # We determine the 'quantity' relevant to the tier based on unit logic
        if price_config.unit == FinishingPrice.PricingUnit.PER_SHEET:
            tier_qty = total_sheets_in_item
        elif price_config.unit == FinishingPrice.PricingUnit.PER_PIECE:
            tier_qty = total_quote_qty
        else:
            tier_qty = 1 # Per job usually doesn't tier, but could

        # Look for applicable tier
        tier = PricingTier.objects.filter(
            finishing_service=price_config,
            min_quantity__lte=tier_qty
        ).filter(
            Q(max_quantity__gte=tier_qty) | Q(max_quantity__isnull=True)
        ).first()

        rate = tier.price_per_unit if tier else price_config.price

        # 2. Calculate Total based on Unit Logic
        cost = Decimal("0.00")

        if price_config.unit == FinishingPrice.PricingUnit.PER_SHEET:
            cost = rate * total_sheets_in_item
        
        elif price_config.unit == FinishingPrice.PricingUnit.PER_SIDE:
            # "Per Side" usually implies lamination. 
            # We assume here that 'total_sheets_in_item' accounts for the physical sheets.
            # If the item is duplex, does lamination apply to both sides? 
            # This logic depends on the specific QuoteItemFinishing context which isn't fully detailed.
            # Implementation: Assume Lamination applies to ONE side per sheet unless multiplied elsewhere.
            # For robustness, we treat PER_SIDE same as PER_SHEET here, assuming the user added 
            # "Double Sided Lamination" as the service if needed.
            cost = rate * total_sheets_in_item

        elif price_config.unit == FinishingPrice.PricingUnit.PER_PIECE:
            # e.g. Binding 50 books
            cost = rate * total_quote_qty

        elif price_config.unit == FinishingPrice.PricingUnit.PER_JOB:
            # Flat fee
            cost = rate

        elif price_config.unit == FinishingPrice.PricingUnit.PER_BATCH:
            # e.g. Creasing 1200 sheets, batch size 1000.
            # ceil(1200 / 1000) = 2 batches * rate
            import math
            batches = math.ceil(total_sheets_in_item / price_config.batch_size)
            cost = rate * batches

        # 3. Add Setup Fee & Check Minimum
        cost += price_config.setup_fee
        cost = max(cost, price_config.minimum_order_quantity * rate) # simplified min check
        
        return cost

    def calculate_quote_total(self, quote):
        """
        Main entry point. Iterates items, parts, and finishing to sum totals.
        """
        grand_total = Decimal("0.00")

        for item in quote.items.all():
            item_total = Decimal("0.00")
            
            # A. Calculate Parts (Paper + Print)
            total_sheets_for_item = 0 # Accumulator for finishing calculations
            
            for part in item.parts.all():
                part_cost = self.calculate_part_cost(part)
                part.save() # Persist the imposition/cost data
                item_total += part_cost
                total_sheets_for_item += part.total_sheets_required

            # B. Calculate Finishing
            for finish_item in item.finishing.all():
                cost = self.calculate_finishing_cost(
                    finish_item, 
                    total_sheets_for_item, 
                    item.quantity
                )
                finish_item.calculated_cost = cost
                finish_item.save()
                item_total += cost

            item.calculated_price = item_total
            item.save()
            grand_total += item_total

        quote.net_total = grand_total
        # Placeholder tax (e.g. 16% VAT) - Ideally fetched from Shop settings
        quote.tax_amount = grand_total * Decimal("0.16") 
        quote.grand_total = quote.net_total + quote.tax_amount
        quote.save()
        
        return quote.grand_total