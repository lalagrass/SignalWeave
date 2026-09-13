# Method: identifier_mapping_v1

Used to create one private identity-mapping revision for one already-written
basket snapshot. This method contains no source text and must never alter the
basket membership it is bound to.

For every `declared_identifier` in the basket, return exactly one mapping entry
in the same order:

- `resolved`: provide canonical `venue` and `symbol` only when both are known.
- `unresolved`: set `venue` and `symbol` to null and provide a short reason.
- `not_publicly_listed`: set `venue` and `symbol` to null; an optional reason
  may explain that the declared member is explicitly not publicly tradeable.

Do not add, remove, repeat, reorder, rank, weight, or score members. Do not
claim whether a venue is supported by MarketPulse and do not inspect prices:
`unsupported_venue` and `no_as_of_price` are MarketPulse as-of outcomes, not
SignalWeave identity statuses. A correction is a new immutable mapping revision
with `supersedes_mapping_id`, never an edit to an older mapping or basket.
