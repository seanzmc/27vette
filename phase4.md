Use the 27vette skill.

Refine pricing logic only.

Focus on:
- Option Price Scopes
- Option Pricing
- Pricing
- Variant Option Matrix
- Price Resolver
- Audit Exceptions

Tasks:
1. Use Option Price Scopes as the canonical pricing layer.
2. Use Option Pricing and Pricing only as staging/reference where needed.
3. Build or refine Price Resolver so that pricing is resolved by variant and scoped condition.
4. Flag conflicting or overlapping scopes.
5. Separate:
   - included / no-charge
   - optional priced
   - package-included
   - conditional price
   - unresolved price
6. Do not overwrite source pricing notes without preserving them somewhere.

At the end, summarize:
- what percent of pricing is resolved
- which option families still need decisions
- what price conflicts were found
