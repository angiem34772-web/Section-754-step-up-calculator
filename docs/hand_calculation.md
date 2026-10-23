# Hand calculation: the sample sale

This is the sample sale worked by hand, the way a reviewer would check it on paper. Every number here is asserted in [`tests/test_step_up.py`](../tests/test_step_up.py), so if the code ever drifts from the hand calculation, the tests fail.

All names and amounts are fictional.

## The facts

On **July 1, 2026**, **Alder Creek Family Trust** sells a **10% interest** in **Maple Hollow Partners LP** to **Juniper Ridge Holdings LLC** for **$1,850,000 cash**. The partnership has a Section 754 election in effect and $20,000,000 of mortgage debt, shared by ownership percentage.

Partnership balance sheet on the sale date:

| Asset | Tax basis | Fair market value | Gain / (loss) | Depreciation taken |
|---|---:|---:|---:|---:|
| Cash | 1,200,000 | 1,200,000 | 0 | |
| Rents receivable | 150,000 | 150,000 | 0 | |
| Land | 6,000,000 | 9,500,000 | 3,500,000 | |
| Apartment buildings | 18,000,000 | 26,000,000 | 8,000,000 | 12,000,000 |
| Appliances and furniture | 300,000 | 700,000 | 400,000 | 1,700,000 |
| Water co-op shares | 500,000 | 350,000 | (150,000) | |
| **Total** | **26,150,000** | **37,900,000** | **11,750,000** | |
| Mortgage | (20,000,000) | (20,000,000) | | |
| **Capital** | **6,150,000** | **17,900,000** | | |

## Step 1. Buyer's outside basis (IRC 742, 752(d))

| | |
|---|---:|
| Cash paid | 1,850,000 |
| 10% of the $20,000,000 mortgage | 2,000,000 |
| **Outside basis** | **3,850,000** |

## Step 2. What the price says the whole partnership is worth (Reg. 1.755-1(a)(4), (a)(5))

A 10% interest for $1,850,000 means the equity is worth $18,500,000. Add back the debt and the assets are worth **$38,500,000** in total. The listed assets add up to $37,900,000, so the extra **$600,000 is goodwill** (residual method). Goodwill has a tax basis of zero.

## Step 3. Buyer's share of inside basis (Reg. 1.743-1(d))

Pretend the partnership sold everything for $38,500,000 on the sale date and liquidated.

| | |
|---|---:|
| Cash to the buyer: 10% x (38,500,000 - 20,000,000) | 1,850,000 |
| Less buyer's 10% share of the gain: 10% x (38,500,000 - 26,150,000) | (1,235,000) |
| **Previously taxed capital** | **615,000** |
| Plus 10% share of the mortgage | 2,000,000 |
| **Share of inside basis** | **2,615,000** |

Check: 10% of the tax capital account (6,150,000) is also 615,000.

## Step 4. The 743(b) adjustment (Reg. 1.743-1(b))

3,850,000 - 2,615,000 = **1,235,000**

Without a 754 election, the buyer would pay for $1,235,000 of built-in gain and then be taxed on it again when the partnership sells or depreciates the assets. The adjustment fixes that, for the buyer only.

## Step 5. Split between the two classes (Reg. 1.755-1(b)(2))

Depreciation recapture is treated as its own ordinary income asset. The furniture's gain of 400,000 is less than the 1,700,000 of depreciation taken, so all of it is Section 1245 recapture.

| Class | How | Amount |
|---|---|---:|
| Ordinary income property | 10% x 400,000 recapture (receivables have no gain) | 40,000 |
| Capital gain property | 1,235,000 - 40,000 | 1,195,000 |

## Step 6. Allocate within each class (Reg. 1.755-1(b)(3))

Each asset gets the buyer's share of its own gain or loss. Here those shares add up exactly to each class total, so no pro rata true-up is needed (the tests also cover a sale where it is).

| Asset | Buyer's share of gain / (loss) | 743(b) adjustment |
|---|---:|---:|
| Appliances and furniture (recapture) | 40,000 | 40,000 |
| Land | 350,000 | 350,000 |
| Apartment buildings | 800,000 | 800,000 |
| Water co-op shares | (15,000) | (15,000) |
| Goodwill | 60,000 | 60,000 |
| **Total** | | **1,235,000** |

Cash can't take a basis adjustment, and the receivables have no built-in gain.

## Step 7. The buyer's extra deductions (Reg. 1.743-1(j)(4))

A step-up on depreciable property is treated as newly purchased property placed in service on the sale date, so its recovery period starts fresh.

| Asset | Step-up | Method | 2026 | 2027 |
|---|---:|---|---:|---:|
| Apartment buildings | 800,000 | 27.5-year straight line, mid-month: 800,000 / 27.5 x 5.5/12 in 2026 | 13,333 | 29,091 |
| Appliances and furniture | 40,000 | 5-year MACRS, 200% declining balance, half-year: 20%, 32% | 8,000 | 12,800 |
| Goodwill | 60,000 | 15-year Section 197 amortization: 60,000 / 180 x 6 months in 2026 | 2,000 | 4,000 |
| Land | 350,000 | Not depreciable; reduces the buyer's gain if the land is sold | | |
| Water co-op shares | (15,000) | Not depreciable; increases the buyer's gain if the shares are sold | | |
| **Total** | | | **23,333** | **45,891** |

Furniture continues at 19.2%, 11.52%, 11.52%, 5.76% (7,680, 4,608, 4,608, 2,304).

## The seller's side (IRC 741, 751(a), Reg. 1.1(h)-1)

The seller's outside basis is $2,700,000 (from the seller's own records; it doesn't have to equal the buyer's inside share).

| | |
|---|---:|
| Amount realized: 1,850,000 cash + 2,000,000 debt relief | 3,850,000 |
| Less outside basis | (2,700,000) |
| **Total gain** | **1,150,000** |
| Ordinary income from hot assets (10% of the furniture recapture) | 40,000 |
| Capital gain | 1,110,000 |
| of which unrecaptured Section 1250 gain, taxed at up to 25%: 10% x 8,000,000 building gain (less than the 12,000,000 depreciation taken) | 800,000 |
| of which other long-term capital gain | 310,000 |

Because part of the gain is ordinary under Section 751, the partnership files Form 8308 for the sale.
