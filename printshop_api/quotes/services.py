# quotes/services.py
"""
Quote calculation service.

Calculates costs based on:
- Printing (per side from PrintingPrice)
- Paper (from PaperPrice or PaperStock)
- Finishing (from FinishingService)
"""

import math
from decimal import Decimal

from pricing.models import PrintingPrice, PaperPrice, FinishingService


class QuoteCalculator:
    """
    Service class to calculate costs for quote items.
    """

    @staticmethod
    def calculate_imposition(
        part_width: Decimal, 
        part_height: Decimal, 
        stock_width: Decimal, 
        stock_height: Decimal
    ) -> int:
        """
        Calculate how many items fit on a stock sheet (N-Up).
        
        Tries both orientations to find best fit.
        """
        pw, ph = float(part_width), float(part_height)
        sw, sh = float(stock_width), float(stock_height)

        # Check if item is too big
        if pw > sw and pw > sh:
            return 0
        if ph > sw and ph > sh:
            return 0

        # Option A: Standard orientation
        count_a = int(sw // pw) * int(sh // ph)

        # Option B: Rotated orientation
        count_b = int(sw // ph) * int(sh // pw)

        return max(count_a, count_b, 1)

    def calculate_part_cost(self, part) -> Decimal:
        """
        Calculate cost for a quote item part.
        
        Includes:
        - Paper cost (from stock or paper price)
        - Printing cost (from printing price)
        
        Updates the part instance but does NOT save it.
        """
        shop = part.item.quote.shop
        quantity = part.item.quantity
        
        # 1. Determine paper stock/size to use
        stock = part.paper_stock
        
        if stock:
            stock_width = stock.width_mm
            stock_height = stock.height_mm
            paper_gsm = stock.gsm
            sheet_size = stock.sheet_size
        else:
            # Use standard A3 if no stock specified
            stock_width = 297
            stock_height = 420
            paper_gsm = part.paper_gsm or 150
            sheet_size = "A3"
        
        # 2. Calculate imposition
        items_per_sheet = self.calculate_imposition(
            part.final_width, 
            part.final_height, 
            Decimal(str(stock_width)), 
            Decimal(str(stock_height))
        )
        
        if items_per_sheet == 0:
            items_per_sheet = 1
        
        part.items_per_sheet = items_per_sheet
        
        # 3. Calculate sheets required
        sheets_required = math.ceil(quantity / items_per_sheet)
        part.total_sheets_required = sheets_required
        
        # 4. Get paper price
        paper_cost = Decimal("0.00")
        try:
            paper_price = PaperPrice.objects.get(
                shop=shop,
                sheet_size=sheet_size,
                gsm=paper_gsm,
                is_active=True
            )
            paper_cost = sheets_required * paper_price.selling_price
        except PaperPrice.DoesNotExist:
            # Use buying price from stock if available
            if stock and stock.buying_price_per_sheet:
                paper_cost = sheets_required * stock.buying_price_per_sheet
        
        # 5. Get printing price
        print_cost = Decimal("0.00")
        try:
            printing_filter = {
                "shop": shop,
                "sheet_size": sheet_size,
                "is_active": True
            }
            if part.machine:
                printing_filter["machine"] = part.machine
            
            print_price = PrintingPrice.objects.filter(**printing_filter).first()
            
            if print_price:
                sides = 2 if part.print_sides == "DOUBLE" else 1
                rate = print_price.selling_price_per_side * sides
                print_cost = sheets_required * rate
        except Exception:
            pass
        
        # 6. Calculate total
        total_part_cost = paper_cost + print_cost
        part.part_cost = total_part_cost
        
        return total_part_cost

    def calculate_finishing_cost(
        self, 
        finishing_item, 
        total_sheets: int, 
        quantity: int
    ) -> Decimal:
        """
        Calculate cost for a finishing service.
        """
        service = finishing_item.finishing_service
        
        if service.charge_by == FinishingService.ChargeBy.PER_JOB:
            cost = service.selling_price
        elif service.charge_by == FinishingService.ChargeBy.PER_PIECE:
            cost = service.selling_price * quantity
        else:  # PER_SHEET
            cost = service.selling_price * total_sheets
        
        return cost

    def calculate_quote_total(self, quote):
        """
        Calculate total for entire quote.
        
        Iterates through items, parts, and finishing to sum costs.
        """
        grand_total = Decimal("0.00")

        for item in quote.items.all():
            item_total = Decimal("0.00")
            total_sheets = 0
            
            # Calculate parts (paper + printing)
            for part in item.parts.all():
                part_cost = self.calculate_part_cost(part)
                part.save()
                item_total += part_cost
                total_sheets += part.total_sheets_required

            # Calculate finishing
            for finishing in item.finishing.all():
                cost = self.calculate_finishing_cost(
                    finishing, 
                    total_sheets, 
                    item.quantity
                )
                finishing.calculated_cost = cost
                finishing.save()
                item_total += cost

            item.calculated_price = item_total
            item.save()
            grand_total += item_total

        # Apply tax
        quote.net_total = grand_total
        quote.tax_amount = grand_total * (quote.tax_rate / 100)
        quote.grand_total = quote.net_total + quote.tax_amount - quote.discount_amount
        quote.save()
        
        return quote.grand_total


class SimpleQuoteCalculator:
    """
    Simple calculator for quick quotes (no imposition).
    
    Use PriceCalculator from pricing.models for even simpler calculations.
    """
    
    @staticmethod
    def calculate(
        shop,
        sheet_size: str,
        gsm: int,
        quantity: int,
        sides: int = 1,
        paper_type: str = "GLOSS",
        finishing_ids: list = None
    ) -> dict:
        """
        Quick price calculation.
        
        Returns breakdown of costs.
        """
        from pricing.models import PriceCalculator
        
        return PriceCalculator.calculate(
            shop=shop,
            sheet_size=sheet_size,
            gsm=gsm,
            quantity=quantity,
            sides=sides,
            paper_type=paper_type,
            finishing_ids=finishing_ids
        )
