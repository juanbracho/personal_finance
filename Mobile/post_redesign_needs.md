 Here's what I'm reading from your prompt + the screenshot:                                                                                                   
                                                                                                                                                               
  ---                                                                                                                                                          
  1. Budget Health — double-counting bug                                                                                                                       
  The bar shows Initial $10,710 + $2,000 unexpected = $12,710 effective budget, but actual spending shows $10,324. You said you manually set ~$9k budget and   
  unexpected ~$11k total should give ~$11k effective, not $12,710. The mobile app is pulling budget data from the same API as the web app — need to trace      
  whether the initial budget figure is being double-counted (e.g. summing budget_templates + unexpected_expenses incorrectly, or including inactive
  categories).

  2. Spending by Type — hide zero-value types
  "Business $0" and "Savings $0" cards are showing. Filter the type cards to only render types where amount > 0. Also, if you've added a custom type (e.g.
  "Unexpected") with actual transactions, it won't appear here at all since the type cards are hardcoded to the 4 defaults.

  3. Spending by Type — dynamic types
  The four cards (Needs / Wants / Business / Savings) are hardcoded in the mobile UI. Since the web app now supports custom types stored in custom_types table,
   the mobile should fetch types dynamically from the same API endpoint and render cards for whatever types exist with data.

  4. Transactions / History — Type field
  The Record and History screens need to reflect custom types in any type picker or type display — same dynamic fetch from the API instead of a hardcoded list
  of 4.

  ---
  Those are the four distinct things to address.