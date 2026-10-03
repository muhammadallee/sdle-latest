# Order Export Service

## Purpose

Finance staff currently rebuild the weekly order summary by hand from several exports, which is slow and
produces mismatched totals. This service produces one consistent export of paid orders, with tax shown,
for a chosen date range.

## Scope

In scope:

- Exporting paid orders for a date range as a CSV file
- Showing, for each order, the amount charged and the sales tax applied
- Re-running an export for a past date range with the same result

Out of scope:

- Refund processing or chargebacks
- Exporting unpaid or cancelled orders
- Producing tax filings

## Data Model

An **Order** has: `id` (unique), `placed_on` (date), `customer_id` (string), `amount_charged` (decimal,
two places), `sales_tax` (decimal, two places) and `status` (`PAID`, `UNPAID` or `CANCELLED`).

An **Export** has: `id` (unique), `from_date`, `to_date`, `requested_by` (employee id) and `created_at`.

## Constraints

- Must run inside the existing internal Kubernetes cluster.
- Must authenticate staff through the company's identity system, with no separate login.
- No new paid third-party services beyond those named in this document.

## Compatibility

- The CSV column order must match the layout finance already uses: order id, date, customer id, amount,
  tax.
- Amounts are exchanged as decimals with two places and a point as the separator.

## Dependencies

- Charges are taken through a payment provider, and the export reads the charge status from it.
- Sales tax is computed by a third-party tax service.
- Staff sign in through the company's identity system.

## Security and Data Handling

- Only authenticated finance staff may request an export.
- Exports contain customer ids but no names or contact details.
- Export files are deleted from the service after 24 hours.

## Non-Functional Requirements

- An export of 50,000 orders must complete within 60 seconds.
- The service must support up to 5 concurrent export requests.

## Acceptance

1. AC-1: Requesting an export for a date range returns a CSV containing only orders with status `PAID`
   placed within that range.
2. AC-2: Every exported row shows the amount charged and the sales tax applied to that order.
3. AC-3: Re-running an export for a past range returns a file identical to the first run.
4. AC-4: A request from a user who is not finance staff is rejected with a 403.
