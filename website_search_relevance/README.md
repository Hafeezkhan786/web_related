# Website Search Relevance & Priority for Odoo / Odoo.sh

## Problem Solved
When searching for products (e.g. `Panadol`) on the website search bar:
1. Irrelevant products (e.g. `Actifed P Cold Tablet`, `Flueze Sachet`) appear before the actual `Panadol` products in the autocomplete suggestion list.
2. This happens because Odoo searches descriptions by default and sorts matching results alphabetically (`name ASC`) rather than by search relevance/rank.
3. On Odoo.sh, PostgreSQL's `pg_trgm` fuzzy matching is active, which causes broad description matches to populate the limited autocomplete dropdown (limit 5).

## Solution Provided by this Module
1. **Intelligent Relevance Ranking**:
   - **Rank 1**: Exact name match.
   - **Rank 2**: Name starts with search term (e.g., `Panadol 500mg Tablet`).
   - **Rank 3**: Name contains search term as a whole word (e.g., `GSK Panadol`).
   - **Rank 4**: Substring match in name or SKU code.
   - **Rank 5**: Matched only through description or generic tags.
2. **Expanded Pre-fetch Pool**:
   - Fetches a broader batch of candidates before sorting, ensuring exact name matches aren't discarded by database `LIMIT 5` before relevance ranking.
3. **Fuzzy Search Optimization**:
   - Prevents description text from polluting typo suggestions on Odoo.sh.
4. **Configurable Settings**:
   - Adds toggle options in **Website > Configuration > Settings > Product Search & Relevance**.

## Installation on Odoo.sh
1. Copy the `website_search_relevance` folder into your custom addons directory (e.g., `custom_addons` or root of your Git repository).
2. Commit and push the branch to your Odoo.sh Git repository:
   ```bash
   git add website_search_relevance
   git commit -m "feat: add website_search_relevance module"
   git push origin <your-branch-name>
   ```
3. In Odoo backend, go to **Apps**, click **Update Apps List**, search for `Website Search Relevance & Priority`, and click **Activate / Install**.
4. Test searching `pnadol` or `panadol` in your website search bar.
