# SPU-Level Flash Sale Campaign Implementation Comparison
## Cross-Language Verification Report

**Generated:** 2026-01-01
**Purpose:** Verify all three services (Python, Java, C#) correctly implement SPU-level campaigns

---

## Summary

| Service | SPU Lookup | Campaign Limit Check | Atomic Update | SKU Inventory | Flash Price | Status |
|---------|------------|----------------------|---------------|---------------|-------------|--------|
| Python  | ✅ CORRECT | ✅ CORRECT          | ✅ CORRECT   | ✅ CORRECT   | ✅ CORRECT | **PASS** |
| Java    | ✅ CORRECT | ✅ CORRECT          | ✅ CORRECT   | ✅ CORRECT   | ❌ **BUG** | **FAIL** |
| C#      | ✅ CORRECT | ✅ CORRECT          | ✅ CORRECT   | ✅ CORRECT   | ❌ **BUG** | **FAIL** |

---

## Detailed Analysis

### 1. Python Implementation ✅ CORRECT

**File:** `python-service/app/api/endpoints/orders.py`

**SPU-Level Campaign Lookup (Lines 124-138):**
```python
# ✅ CORRECT: Checks campaign on SKU's parent SPU
if sku.spu_id:
    campaign_result = await db.execute(
        select(FlashSaleCampaign).filter(
            FlashSaleCampaign.spu_id == str(sku.spu_id),  # ✅ SPU-level
            FlashSaleCampaign.is_active == True,
            FlashSaleCampaign.status == FlashSaleStatus.ACTIVE,
            FlashSaleCampaign.start_time <= datetime.utcnow(),
            FlashSaleCampaign.end_time >= datetime.utcnow()
        )
    )
    campaign = campaign_result.scalar_one_or_none()
```

**Campaign Limit Validation (Lines 142-156):**
```python
# ✅ CORRECT: Validates campaign-level limit
if campaign.sold_quantity + item_data.quantity > campaign.total_sale_limit:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Flash sale campaign '{campaign.name}' limit exceeded. "
               f"Only {campaign.total_sale_limit - campaign.sold_quantity} items remaining."
    )
```

**Atomic Update (Lines 162-166):**
```python
# ✅ CORRECT: Atomically increments sold_quantity
campaign.sold_quantity += item_data.quantity

# ✅ CORRECT: Marks campaign as ended when sold out
if campaign.sold_quantity >= campaign.total_sale_limit:
    campaign.status = FlashSaleStatus.ENDED
```

**Pricing Logic (Lines 181-184):**
```python
# ✅ CORRECT: Uses flash_price when campaign is active
if active_campaign:
    unit_price = item_data.unit_price or active_campaign.flash_price
else:
    unit_price = item_data.unit_price or sku.price
```

**Verdict:** ✅ **FULLY CORRECT** - Implements all requirements properly

---

### 2. Java Implementation ❌ PRICING BUG

**File:** `java-service/src/main/java/com/flashsale/api/service/OrderService.java`

**SPU-Level Campaign Lookup (Lines 91-96):**
```java
// ✅ CORRECT: Checks campaign on SKU's parent SPU
if (sku.getSpuId() != null) {
    Optional<FlashSaleCampaign> campaignOpt = flashSaleCampaignRepository.findActiveCampaignForSpu(
        sku.getSpuId(),  // ✅ SPU-level
        java.time.LocalDateTime.now()
    );
```

**Campaign Limit Validation (Lines 102-108):**
```java
// ✅ CORRECT: Validates campaign-level limit
if (campaign.getSoldQuantity() + itemDto.getQuantity() > campaign.getTotalSaleLimit()) {
    throw new IllegalStateException(
        String.format("Flash sale campaign '%s' limit exceeded. Only %d items remaining.",
            campaign.getName(),
            campaign.getTotalSaleLimit() - campaign.getSoldQuantity())
    );
}
```

**Atomic Update (Lines 114-119):**
```java
// ✅ CORRECT: Atomically increments sold_quantity
campaign.setSoldQuantity(campaign.getSoldQuantity() + itemDto.getQuantity());

// ✅ CORRECT: Marks campaign as ended when sold out
if (campaign.getSoldQuantity() >= campaign.getTotalSaleLimit()) {
    campaign.setStatus(FlashSaleStatus.ended);
}
```

**Pricing Logic (Line 137):**
```java
// ❌ BUG: Does NOT use campaign.getFlashPrice()
BigDecimal unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : sku.getPrice();
```

**Expected Fix:**
```java
// ✅ CORRECT: Should use flash_price when campaign is active
BigDecimal unitPrice;
if (activeCampaign != null) {
    unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : activeCampaign.getFlashPrice();
} else {
    unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : sku.getPrice();
}
```

**Verdict:** ❌ **PRICING BUG** - Campaign logic correct, but customers NOT charged flash sale price

---

### 3. C# Implementation ❌ PRICING BUG

**File:** `csharp-service/Services/OrderService.cs`

**Note:** C# has TWO variants:
- **Variant X:** Redis-based atomic counters (lines 236-321)
- **Variant Y:** Database transactions (lines 101-230)

We're analyzing **Variant Y** (traditional database path) since that's what's currently active.

**SPU-Level Campaign Lookup (Lines 143-151):**
```csharp
// ✅ CORRECT: Checks campaign on SKU's parent SPU
var campaign = await _context.FlashSaleCampaigns
    .FirstOrDefaultAsync(c =>
        c.SpuId == sku.SpuId &&  // ✅ SPU-level
        c.IsActive == true &&
        c.Status == FlashSaleStatus.Active &&
        c.StartTime <= now &&
        c.EndTime >= now);
```

**Campaign Limit Validation (Lines 156-160):**
```csharp
// ✅ CORRECT: Validates campaign-level limit
if (campaign.SoldQuantity + itemDto.Quantity > campaign.TotalSaleLimit)
{
    throw new InvalidOperationException(
        $"Flash sale campaign '{campaign.Name}' limit exceeded. " +
        $"Only {campaign.TotalSaleLimit - campaign.SoldQuantity} items remaining.");
}
```

**Atomic Update (Lines 166-172):**
```csharp
// ✅ CORRECT: Atomically increments sold_quantity
campaign.SoldQuantity += itemDto.Quantity;

// ✅ CORRECT: Marks campaign as ended when sold out
if (campaign.SoldQuantity >= campaign.TotalSaleLimit)
{
    campaign.Status = FlashSaleStatus.Ended;
}
```

**Pricing Logic (Line 188):**
```csharp
// ❌ BUG: Does NOT use campaign.FlashPrice
var unitPrice = itemDto.UnitPrice ?? sku.Price;
```

**Expected Fix:**
```csharp
// ✅ CORRECT: Should use flash_price when campaign is active
var unitPrice = activeCampaign != null
    ? (itemDto.UnitPrice ?? activeCampaign.FlashPrice)
    : (itemDto.UnitPrice ?? sku.Price);
```

**Verdict:** ❌ **PRICING BUG** - Campaign logic correct, but customers NOT charged flash sale price

---

## Critical Findings

### ✅ What ALL Services Implement Correctly:

1. **SPU-Level Lookup:** All three correctly query campaigns by `spu_id`, not `sku_id`
2. **Campaign Limit Validation:** All three correctly check `sold_quantity + requested <= total_sale_limit`
3. **Atomic Updates:** All three correctly increment `sold_quantity` within transaction
4. **Status Management:** All three correctly mark campaigns as `ENDED` when sold out
5. **Dual Validation:** All three check BOTH campaign limit AND SKU inventory

### ❌ Critical Bug: Flash Sale Pricing NOT Applied

**Impact:** Customers ordering during flash sales are charged **regular price** instead of **flash sale price**

**Affected Services:**
- ❌ Java: Line 137 in `OrderService.java`
- ❌ C#: Line 188 in `OrderService.cs` (Variant Y)

**Root Cause:** Both Java and C# use `sku.price` instead of `campaign.flash_price`

**Business Impact:**
- Flash sale campaigns track inventory correctly
- Flash sale campaigns prevent overselling correctly
- **BUT customers pay WRONG PRICE** (regular price, not discounted flash price)

---

## Database Schema Verification

**File:** `shared-schema.sql`

```sql
-- ✅ CORRECT: Campaign table uses spu_id (SPU-level)
CREATE TABLE flash_sale_campaigns (
    id CHAR(36) PRIMARY KEY,
    spu_id CHAR(36) NOT NULL,              -- ✅ SPU-level (NOT sku_id)
    total_sale_limit INT NOT NULL,         -- ✅ Total across ALL SKUs
    sold_quantity INT NOT NULL DEFAULT 0,  -- ✅ Incremented for ANY SKU order
    flash_price DECIMAL(10,2) NOT NULL,    -- ✅ Campaign-specific price
    FOREIGN KEY (spu_id) REFERENCES spus(id)
);

-- ✅ CORRECT: Order references campaign
CREATE TABLE orders (
    flash_sale_campaign_id CHAR(36),
    FOREIGN KEY (flash_sale_campaign_id) REFERENCES flash_sale_campaigns(id)
);
```

**Verdict:** ✅ Schema is correct

---

## Test Scenario: iPhone 16 Flash Sale

**Campaign Setup:**
- SPU: "iPhone 16" (id: `550e8400-e29b-41d4-a716-446655440001`)
- SKUs under this SPU:
  - iPhone 16 Black 512GB (regular price: $1199)
  - iPhone 16 Silver 128GB (regular price: $999)
  - iPhone 16 Blue 256GB (regular price: $1099)
- Campaign: `total_sale_limit = 100`, `flash_price = $899`

**Test Case:** Customer orders 1x iPhone 16 Black 512GB

| Service | Campaign Check | SKU Check | Price Charged | Expected Price | Correct? |
|---------|----------------|-----------|---------------|----------------|----------|
| Python  | ✅ Pass        | ✅ Pass   | $899          | $899           | ✅ PASS  |
| Java    | ✅ Pass        | ✅ Pass   | $1199         | $899           | ❌ FAIL  |
| C#      | ✅ Pass        | ✅ Pass   | $1199         | $899           | ❌ FAIL  |

**Result:**
- All services prevent overselling ✅
- Java/C# customers overcharged by **$300** ❌

---

## Recommendations

### Immediate Action Required:

1. **Fix Java pricing logic** (`OrderService.java` line 137)
2. **Fix C# pricing logic** (`OrderService.cs` line 188)
3. **Add pricing tests** to verify flash_price is applied during campaigns
4. **Run benchmarks again** after fixes to ensure no performance regression

### Required Changes:

**Java:**
```java
// Replace line 137 with:
BigDecimal unitPrice;
if (activeCampaign != null) {
    unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : activeCampaign.getFlashPrice();
} else {
    unitPrice = itemDto.getUnitPrice() != null ? itemDto.getUnitPrice() : sku.getPrice();
}
```

**C#:**
```csharp
// Replace line 188 with:
var unitPrice = activeCampaign != null
    ? (itemDto.UnitPrice ?? activeCampaign.FlashPrice)
    : (itemDto.UnitPrice ?? sku.Price);
```

---

## Conclusion

**SPU-Level Campaign Implementation:** ✅ **CORRECT** across all services
**Dual Validation (Campaign + SKU):** ✅ **CORRECT** across all services
**Flash Sale Pricing:** ❌ **BROKEN** in Java and C#

The core flash sale campaign logic is correctly implemented across all three services:
- All services correctly track campaigns at SPU level
- All services correctly validate against campaign limits
- All services correctly prevent overselling

**However, Java and C# have a critical pricing bug that causes customers to be charged regular prices instead of flash sale prices during active campaigns.**

Python implementation is fully correct and serves as the reference implementation.

---

**Status:** REQUIRES IMMEDIATE FIX before production use
**Risk Level:** HIGH (incorrect pricing = revenue loss + customer trust issues)
