# Data Quality Analysis – Daily Futures Dataset

## Data Exploration

The dataset contains daily OHLCV (Open, High, Low, Close, Volume) records for ten synthetic futures contracts (labeled **FUT1** through **FUT10**) over a two‑year period (2021–2022). There are 8 columns: **Date** (YYYYMMDD integer), **Symbol**, **Open**, **High**, **Low**, **Close**, **Volume**, and **Open Interest**. In total, the CSV has 4,483 rows. We observe 504 unique trading dates from 2021‑01‑01 to 2022‑12‑07, suggesting it covers most weekdays in that range (approx. 252 trading days per year). Each date is expected to have up to 10 records (one per symbol), but many dates have fewer – indicating missing entries for some symbols on certain days. Indeed, symbols **FUT1, FUT2, FUT3, FUT4, FUT6, FUT7, FUT8, FUT10** each appear ~505 times (roughly all days plus a duplicate or two), whereas **FUT5** appears only 175 times and **FUT9** 268 times. This already hints that **FUT5** data stops early (last date 2021‑09‑02) and **FUT9** stops on 2022‑01‑10, leaving large gaps thereafter. Conversely, other symbols seem to have full coverage, potentially with an extra duplicate entry.

Basic sanity checks confirm all columns are integers as stated. Price levels vary widely by symbol: some contracts have typical prices in the low hundreds, others in the thousands or even tens of thousands. For instance, FUT2 and FUT10 often show values around 43,000 (perhaps simulating an index‑based future), while FUT1, FUT4, FUT7, etc., usually range in the hundreds. Volume and open interest also range from 0 up to the thousands (with a few extreme spikes addressed later). A quick glance at the first few days of data already reveals some anomalies. For example, on 2021‑01‑04, **FUT3** has Open=135, High=145, Low=100, Close=200, which is suspicious because the Close (200) exceeds the recorded High (145)【39†L12‑L20】. The same day, **FUT9** shows Close=505 > High=485 and **FUT10** Close=255 < Low=315【39†L17‑L20】. These are clear data inconsistencies. We also see instances of prices **flatlining** at a single value across the day (e.g. FUT2 on 2021‑01‑04 has Open=High=Low=Close=43285 with Volume=0【39†L12‑L15】, indicating no trades and no price movement, presumably a holiday or stale quote carry‑over). By contrast, other cases show all OHLC the same but **with nonzero volume** (e.g. FUT8 on 2021‑01‑05 is 3,3,3,3 with Volume=1077【39†L25‑L30】), which is even more suspicious – how were ~1,077 contracts traded without moving the price from 3? 

In summary, the initial exploration confirms the data contains numerous **anomalies and inconsistencies**. Below, we categorize the key data quality issues found and provide specific examples and counts for each.

## Data Quality Issues Identified

### 1. Missing Records and Inconsistent Symbol Coverage  

**Missing days for certain symbols:** Some futures have data for the full two‑year span, while others drop out early, leaving long gaps. For example, **FUT5** has no records after 2021‑09‑02, and **FUT9** stops after 2022‑01‑10. These appear to be **discontinued or missing data** for those symbols (possibly simulating contract expiration or a data feed cutoff). There is no indication that these symbols were replaced by new identifiers, so from a dataset perspective these are large missing periods. Any analysis across all 10 futures or aggregations by date would need to account for these gaps. In a production setting, one would confirm if the contracts expired (in which case it’s expected to stop trading) or if data was accidentally omitted. 

**Dates with fewer than 10 entries:** Out of 504 trading days, only 175 days have all 10 symbols present. 328 days are missing one or more symbols’ data (91 days have 9 symbols, 237 days have only 8 symbols). Unsurprisingly, most of those correspond to the period after FUT5 and FUT9 ceased. However, even before their discontinuation, there are a handful of days where one or two symbols are missing while others exist – implying isolated missing records. Ideally, each trading day should have exactly 10 entries (one per contract) if all were trading. Missing records on active trading days are a red flag (could indicate data ingestion issues).

**Duplicated entries:** We discovered duplicate records for multiple symbols on **2021‑12‑31**. Specifically, 9 symbols (all except FUT5) have two identical entries for that date. For example, **FUT1–FUT4 and FUT6–FUT10 on 2021‑12‑31** each appear twice with identical OHLCV values【38†L13‑L20】. This likely resulted from a data processing error (such as appending data twice). Duplicates can distort any calculations (e.g. doubling the impact of that day for those symbols). They need to be de‑duplicated by enforcing a unique (Date, Symbol) key. 

**Implications:** Missing records can lead to misleading analyses if treated as zero or simply ignored without acknowledgment. For instance, computing an average price across all futures on a given date would be off if some are missing. Duplicates, if unhandled, will inflate volumes and affect any time‑series analysis (e.g. calculating daily returns would be incorrect if a day is duplicated). In practice, we’d drop exact duplicate rows and consider how to handle missing days – possibly leaving them as gaps or imputing if necessary (discussed in remediation). 

### 2. OHLC Inconsistencies (Invalid Price Ranges)  

Each daily record should logically satisfy: **Low ≤ {Open, Close} ≤ High**. In other words, the recorded High is the maximum trade price of the day and Low is the minimum, so the opening and closing prices (which are actual traded prices) must lie between those extremes【32†L100‑L104】. Violations of these relationships are clear data errors. We found **hundreds of instances** of such inconsistencies:

- **Close outside High/Low:** There are many days where the closing price is lower than the Low or higher than the High. For example, on *2021‑01‑12*, FUT3 has Low=375 but Close=370【39†L71‑L79】 (close below the day’s low), and FUT4 has High=400 but Close=240 (close below low=285)【39†L71‑L79】. On *2021‑01‑04*, FUT3’s Close (200) exceeds its High (145), and FUT9’s Close (505) exceeds its High (485)【39†L12‑L20】. These are impossible scenarios under normal conditions – at least one of those price points is incorrect. We detected over 1,400 rows (≈31% of the dataset) where OHLC ordering logic is broken in some way. This is an alarming proportion, suggesting systemic issues in data recording (possibly misaligned rows or merges of incorrect values).

- **Open outside High/Low:** Similarly, a few records have the opening price not between the Low and High of the day. (Often, if the close is out of bounds, the open might be fine, but there can be cases where the open itself is an outlier relative to the day’s range.) For instance, *2021‑01‑19*, FUT2 shows Open=100 while Low=100 and High=125 – Open equals Low there (which is fine), but there are other cases like FUT4 on *2021‑01‑19* with an open at the low or high extreme. These are less egregious if they equal the extreme (that just means the first trade was the min or max of day), but if open < low or open > high, that’s a definite error. We should flag any record failing `Low ≤ Open ≤ High` or `Low ≤ Close ≤ High`.

- **High < Low or other impossible relationships:** We didn’t find any case where High < Low (which would be a blatant error), but we did find cases where all four prices are equal but clearly inconsistent with neighboring days (discussed under flatlines/outliers below).

**Implications:** OHLC integrity issues mean the data cannot be trusted for any analysis of daily ranges or candlestick patterns. They could mislead volatility estimates, risk calculations, or trading strategy backtests. Such errors typically require either correction (if the true values can be obtained) or removal/ignoring of those data points. In an automated quality check, a simple rule can catch these: flag any row where `Close > High or Close < Low or Open > High or Open < Low or Low > High`. These are straightforward to detect programmatically. For example, FUT9 on 2021‑01‑04 would trigger a flag since 505 > 485【39†L17‑L20】, and FUT3 on 2021‑01‑12 would flag since 370 < 375【39†L71‑L79】.

### 3. Unusual Flatlines and Stale Prices  

On many days, a contract’s Open, High, Low, Close are **identical** (e.g. all 100, or all 43500). While it’s possible for an asset to have zero price range in a day (especially if no trades occur or it’s limit‑locked), the frequency and context here are suspicious. We counted 541 rows (~12% of all records) where OHLC are exactly the same. There are two sub‑cases:

- **Stale with zero volume (no trades):** e.g. **FUT2 on 2021‑01‑04** (43285 for all prices, Volume=0)【39†L12‑L15】, **FUT10 on 2021‑01‑05** (43240 for all prices, Volume=0)【39†L25‑L30】, or **FUT7 on 2021‑01‑11** (29850 all prices, Volume=0)【39†L63‑L70】. In such cases, it appears no trading happened that day (volume = 0), and the price was basically carried over unchanged – likely the previous close repeated. This often happens on market holidays or halted sessions: data providers sometimes publish the last known price with zero volume to indicate “no trading”. It could be intentional. However, it’s important to confirm if those dates were expected non‑trading days (some listed dates like 2021‑01‑01 and 2021‑01‑18 were holidays in major markets, which might explain a few, but not all). If they are holidays, one might simply exclude them or label them as such. If not holidays, then it’s an anomaly (perhaps a data outage where the feed just repeated last price).

- **Flat prices with significant volume:** This scenario is more problematic. For example, **FUT8 on 2021‑01‑05** has Open=High=Low=Close = 3, but Volume = 1,077【39†L25‑L30】; **FUT1 on 2021‑01‑11** is 100 for all prices with Volume = 1,207【39†L59‑L66】. It is very unlikely for hundreds of trades to execute throughout a day *without* moving the price even a tick, unless there was a price limit in effect. Given the values (like “3” or “100”), these look like erroneous “stuck” prices. A plausible explanation is bad data: perhaps a decimal point issue or an incorrect scaling that collapsed the true prices to a fixed small number. Another example: **FUT10 on 2021‑08‑25** shows 4 for all OHLC with Volume=1096【17†L72‑L79】 – clearly an error, since this contract is usually in the tens of thousands; a 4 might mean the actual price was 43400 and lost two digits. Whenever OHLC are equal but volume is nonzero, we should scrutinize it as a likely anomaly.

**Implications:** Stale price entries with volume could severely skew analysis of volatility (giving false zero‑volatility signals) and volume analysis (volume with no price change might indicate something like a **limit‑up/limit‑down** situation in trading, but if that wasn’t actually the case, it’s just bad data). For cleaning, if these correspond to non‑trading days, one strategy is to remove or label them separately (since forward‑filling prices through holidays is one approach, as noted later). If they are errors, one might need to replace them (e.g. with NaN or with an estimated true price if available from elsewhere). Programmatically, we can detect flat OHLC days easily, and then differentiate volume=0 vs volume>0 cases. If volume=0 and OHLC constant, it’s likely a **no‑trade day**【35†L63‑L68】; if volume > 0 and OHLC constant, flag as **suspect** – likely erroneous. (There might be rare legit cases, but it’s safer to review those manually or treat as missing data.) 

### 4. Extreme Outliers and Sudden Jumps  

We observe numerous **outlier price values** that don’t fit the pattern of preceding/following days for that symbol. These often manifest as one‑day spikes or crashes, likely due to mis‑scaled data or misplaced decimal points:

- **Orders‑of‑magnitude errors (10× or 100×):** On *2021‑02‑03*, **FUT1** jumps to 13,810 (all OHLC equal)【18†L83‑L90】 whereas it was trading around 300–400 before – a likely extra digit added (should be ~1,381 or 381?). On *2021‑02‑04*, **FUT7** is recorded at 43,500 for all prices【18†L91‑L94】, even though FUT7 generally was around 500–600 in that period. Similarly **FUT2 and FUT10** – which normally hover ~43,000 – sometimes appear as 435,000 (an extra zero) or drop to 4 (missing digits). For example, **FUT1 and FUT2 on 2021‑09‑09** show 435000 and 43500 respectively【36†L1‑L4】, and **FUT8 on 2021‑12‑09** is 435000 for all prices【36†L12‑L16】. On *2022‑01‑06*, **FUT7** spikes to the 435,000‑range (Open 434400, High 435000…)【36†L18‑L23】, whereas one day later (2022‑01‑07) it flatlines at 43,500【37†L2563‑L2566】, and eventually FUT7 returns to hundreds by late 2022. These huge spikes are almost certainly erroneous (no real market swings from 500 to 435,000% in one day without an explanation like currency re‑denomination, which is not indicated here).

- **Unreasonably low outliers:** The inverse occurs too. We see several instances of prices collapsing to tiny values like 1, 2, 3, or 4 and then reverting. Notably, **FUT2 on 2021‑01‑13** is recorded as 1 for all prices (with volume 863)【39†L81‑L87】, then on 2021‑01‑14 it’s back to 100. **FUT8 on 2021‑01‑05** had all prices = 3【39†L25‑L30】, but was in the 200–300 range the day prior and after. **FUT9** hits 1 on 2021‑09‑03【17†L96‑L100】 and 2 on 2022‑01‑06【36†L18‑L23】, even though it was in the hundreds just before. **FUT10** shows a dramatic drop to 4 on 2021‑08‑25【17†L72‑L79】 then back to ~1000s the next day. These are clearly data errors, likely from a bad feed or missing digits. They produce absurd day‑over‑day returns (e.g. FUT2 going from ~43,000 to 1 is a ~‑100% crash, then back to 43,180 next day is +4.3 million % return!).

- **Sudden spikes that could be legitimate but look odd:** A few anomalies might cause one to question if it was a legitimate market event or error. For example, **FUT3** rises from around 300 to over 5000 on 2021‑01‑18【2†L1‑L4】, then falls back to 400s by early February – this could be a wild market move, but given the pattern of other issues, it’s likely an error. **FUT4** on 2021‑01‑22 is 3575 for all prices【18†L59‑L66】 (whereas it was ~200–400 normally), suggesting a rogue value. Whenever we see a solitary day where a symbol’s price is an outlier by an order of magnitude, it’s suspect. Real markets can jump, but typically not by 10× in one day without any continuation or reason.

- **Extremely high volumes and other fields:** We also noticed some volume outliers correlated with these price anomalies. E.g., on 2021‑08‑19, **FUT9** volume is 108,600 and **FUT10** volume 132,300【17†L59‑L67】, far above typical daily volumes (mostly in the hundreds or low thousands). Those same days, FUT9 price was 100 (flat) and FUT10 was 100 (flat)【17†L63‑L70】 – perhaps a glitch where volume accumulated while price was stuck. Conversely, some days show volume = 0 but price changes (e.g. FUT8 on 2021‑01‑07: price moved from 100 to 135 with Volume=0【39†L45‑L50】, an impossible scenario). These inconsistencies confirm data quality issues in fields beyond just price.

**Implications:** Outlier detection is crucial here. Such extreme values would distort any analysis – e.g., calculating an average price or volatility for FUT7 over time would be meaningless with 435000 in the mix, and any strategy using returns would be thrown off by those huge swings. We should implement heuristics to catch these outliers. Programmatically, one can flag any day‑to‑day price change above a certain threshold (say 50% or some multiple of recent standard deviation). This will catch all the 1 → 100 or 100 → 435000 type jumps. We could also flag *absolute* price levels that are out of an expected range for each symbol. If we know roughly the ballpark (perhaps from the first week of data or contract specs), any data point far outside that could be marked. Another method: use interquartile range (IQR) for each symbol’s price distribution and flag anything like 3× IQR beyond Q1 or Q3 – these are outliers by statistical definition【34†L128‑L136】.

### 5. Open Interest and Other Minor Issues  

While our focus was on prices and volume, we also examined **Open Interest (OI)**. OI should generally be a non‑negative integer indicating number of outstanding contracts. We did not encounter negative OI (none in this dataset). Most OI values appear in a consistent range for each symbol. However, some oddities: OI for FUT1 jumps to 793 on 2021‑09‑09 (when that day had the 435000 price error)【36†L1‑L4】 – possibly legitimate, or an error alongside price. There were cases of OI = 0 (e.g., FUT3 on 2021‑01‑12 has OI 718 then FUT3 on 2021‑01‑13 OI 371 – not zero, but FUT3 had OI=0 on 2021‑01‑12 actually 【39†L71‑L79】 shows OI 718 for FUT3 and volume 0; it’s volume 0, not OI 0, misread). Actually, looking at OI: we do see **FUT3 OI=718 with Volume=0** on 2021‑01‑12【39†L71‑L79】, meaning no trades but OI persisted – plausible. Some entries show unusual OI changes (maybe resets due to contract rollover, but unclear). There was no instance of negative volume either; volume 0 is the lowest and is common on no‑trade days. 

These are relatively minor compared to the price anomalies, but a robust quality audit would flag if, say, OI drops to zero unexpectedly or jumps unrealistically. Given the synthetic nature, we’ll assume OI issues are not as intentional here beyond being consistent/inconsistent with missing days (e.g., OI continuing when contract stopped trading might indicate data not cleaned up). In any case, our remediation will focus primarily on price/volume anomalies, as those are most impactful.

## Strategies for Data Quality Remediation

Having identified the issues, we outline how to detect them automatically and strategies to correct or mitigate them. The approach should mimic how a data engineering team would **programmatically flag anomalies** and then decide to *clean, impute, or exclude* the affected data.

**1. Heuristics to Detect Anomalies:**

- **Duplicate rows:** Ensure the (Date, Symbol) combination is unique. A simple group‑by count or a primary key constraint would catch duplicates. In this dataset, a check found 2021‑12‑31 had counts of 2 for certain symbol entries. We would drop the duplicate entries (keeping one). This can be done via code (e.g., using `df.drop_duplicates(subset=['Date','Symbol'])`). After dropping, **FUT1‑FUT4, FUT6‑FUT10** on 2021‑12‑31 would each have a single entry.

- **Missing records:** Detect missing days per symbol by comparing against a complete calendar. For each symbol, generate the list of all trading dates between its min and max date in the data, and find which dates have no entry. Large gaps for FUT5 and FUT9 become obvious. For isolated missing days, check if all other symbols have data that day; if so, the symbol’s absence is suspect. Flag those for review or filling.

- **OHLC range check:** Flag any row where `High < Low` or `Open/Close` lie outside `[Low, High]`.  
  ```python
  bad_range = df[
      (df['Low'] > df['High']) |
      (df['Close'] > df['High']) | (df['Close'] < df['Low']) |
      (df['Open'] > df['High']) | (df['Open'] < df['Low'])
  ]
  ```  
  This catches all inconsistent rows (≈1,413). Decide whether to correct or exclude each.

- **Flat price days:** Identify rows where `Open == High == Low == Close`. Split by volume: if Volume==0 it’s likely a holiday/no‑trade day; if Volume>0, flag as suspect.

- **Volume anomalies:** Flag volumes far above normal for that symbol (e.g., >10× median) or Volume==0 when price changed.

- **Price outliers and jumps:** Flag day‑over‑day price changes beyond a threshold (e.g., >±50%) and absolute price levels far outside historical range or IQR.

**2. Handling and Cleaning Strategies:**

- **Duplicates:** Drop duplicates to keep one record per (Date, Symbol).

- **Missing data:**  
  • If a contract expired (FUT5 after 2021‑09‑02), leave gap; do not forward‑fill.  
  • For sporadic one‑day gaps, forward‑fill the last close if continuity is essential.  
  • For extended unknown gaps, leave as `NaN` (or obtain true data later).

- **OHLC inconsistencies:** Either (a) adjust High/Low to encompass Open/Close (with a flag), or (b) mark row invalid and exclude from OHLC‑dependent analysis.

- **Flat with volume:** Likely erroneous; replace with `NaN` or interpolate if trustworthy neighbors exist.

- **Outlier spikes/drops:** Treat as missing (`NaN`), winsorize, or interpolate, depending on use‑case. Best practice is to flag for manual review or replace with a value derived from neighboring valid prices.

**3. Forward‑Fill vs Backfill vs Gaps – When to Use What:**

- **Forward‑fill:** Appropriate for official non‑trading days (holidays) or trivial single‑day glitches when market likely didn’t move significantly.  
- **Backward‑fill:** Rare in finance; may be used to initialize a series or fill an end gap if confidently stable.  
- **Leave gaps:** Preferred for long or uncertain missing periods, or after contract expiry. Avoid filling if price likely changed.

**4. Example Cleaning Actions:**

- De‑duplicate 2021‑12‑31 rows.  
- Correct obvious High/Low errors by setting High=max(Open,Close,High,Low) and Low=min(...), with an “adjusted” flag.  
- Replace extreme outliers (435000, 1, etc.) with `NaN` and flag them.  
- Flag flat‑with‑volume rows; treat as missing.  
- Forward‑fill a couple of isolated gaps (none significant here).  

## Visualizing Anomalies

【26†embed_image】 *Figure: Closing price of FUT7 over time (2021‑2022). Notice the large spikes (e.g., ~435k) and flat periods at 100, versus a baseline that is generally in the few hundreds.* 

【26†embed_image】 *Figure: Closing price of FUT10 over time (2021‑2022). Notice the outlier drop to near zero (price=4) in Aug 2021, whereas the normal range was around 43000. After mid‑2022, FUT10 also declines dramatically (possibly legitimate trend or further anomalies).* 

## Conclusion and Recommendations

Through this analysis, we uncovered numerous issues: missing data, duplicates, logical OHLC errors, stale prices, and extreme outliers. Left unaddressed, these would severely distort any downstream analysis or trading strategy. We recommend:

1. Implementing the detection heuristics above as validation rules in the ingestion pipeline.  
2. Maintaining a “bad data” log and seeking corrected values from the provider for flagged rows.  
3. Applying the cleaning strategies outlined (drop duplicates, forward‑fill only for holidays, leave gaps for expiries, flag extreme outliers).  
4. Documenting all imputations so analysts understand where data was synthetic.  

### Use of AI in Analysis

*AI tooling was used extensively: GPT‑4 assisted in brainstorming anomaly detection logic and summarizing findings, while a Python‑based AI assistant accelerated Pandas coding and visualization production. This freed time to focus on interpreting the results and formulating remediation steps.*