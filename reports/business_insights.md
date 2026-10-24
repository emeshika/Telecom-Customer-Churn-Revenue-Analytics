# Business Insights – Telecom Customer Churn

**Dataset:** 7,043 customers · 26.5% churn rate · $456,117 monthly revenue  
**Revenue at risk:** $139,131/month (30.5% of total revenue)

---

## Insight 1: Month-to-Month Contracts Are the Churn Epicentre

**Finding:**  
Month-to-month customers churn at **42.7%** — 15× the rate of two-year contract customers (2.8%). This single segment accounts for **1,655 of the 1,869 churners (88.6%)** and **$120,847 of the $139,131 monthly revenue at risk (86.8%)**.

**Why it happens:**  
Month-to-month customers have no switching cost. They signed up for flexibility, which means they also leave flexibly. The first moment a competitor offers a lower price or better speed, there is nothing holding them.

**Recommended action:**  
Launch a **6-month loyalty upgrade offer** targeting month-to-month customers who have reached 3–6 months of tenure — the window where churn probability begins to moderate but is still high (see Insight 2). Offer a 10–15% monthly discount in exchange for switching to a one-year contract. At a 20% conversion rate on the 3,875 month-to-month base, this retains ~155 customers/month and recovers roughly **$11,000/month in revenue** — a strong ROI even after the discount cost.

---

## Insight 2: The Critical Churn Window Is the First 12 Months

**Finding:**  
Customers in their first year churn at **47.4%** — nearly one in two. By year 3, churn falls to 21.6%, and by year 5 it is below 7%. The 0–12 month cohort represents **1,037 churners** contributing **$68,954 of monthly revenue at risk**.

**Why it happens:**  
New customers are evaluating whether the service delivers on the promise made during the sales process. Unresolved issues in early tenure — billing confusion, speed expectations, setup friction — drive early disengagement before loyalty forms. This is compounded by the high proportion of month-to-month contracts in the new cohort (most new customers start month-to-month).

**Recommended action:**  
Implement a **structured onboarding programme** with three touchpoints:
- **Day 7:** Automated SMS/app check-in with a quick satisfaction survey.
- **Month 1:** Proactive customer service call for customers with any complaint ticket.
- **Month 3:** Retention offer (e.g. a free month or a speed upgrade trial) for customers who have not yet signed a longer-term contract.

Reducing first-year churn by just 5 percentage points (from 47.4% to 42.4%) saves approximately **~109 customers/month** and **$7,000+ in monthly revenue**.

---

## Insight 3: Fiber Optic Is the Highest-Revenue, Highest-Risk Segment

**Finding:**  
Fiber optic customers churn at **41.9%** — more than double the DSL rate (19.0%) — despite paying significantly more. This segment contributes **$114,300/month of revenue at risk**, the largest of any internet service tier.

**Why it happens:**  
Fiber optic customers pay a premium and have correspondingly high expectations for speed and reliability. When those expectations are not met — or when a competitor matches the price — churn follows quickly. The higher bill also means more financial motivation to switch. Complaint data reinforces this: churned customers average **2.96 complaint tickets** vs 0.73 for retained customers, suggesting service quality incidents are a proximate cause.

**Recommended action:**  
Two parallel actions:

1. **Service quality monitoring:** Flag fiber optic customers who open a second complaint ticket for a priority service callback within 24 hours. Customers who receive a proactive resolution before the third complaint are statistically less likely to churn. This targets the highest-revenue customers at the moment their risk spikes.

2. **Competitive price anchoring:** For fiber optic customers at month 11 (contract renewal point), send a personalised retention offer that benchmarks the total cost of switching (installation fees, new contract setup) against a loyalty discount. Even a 5% discount on a high-ARPU fiber customer is a better outcome than losing them entirely.

---

## Insight 4: Electronic Check Payment Is a Leading Churn Indicator

**Finding:**  
Customers paying by electronic check churn at **45.3%** — three times the rate of customers on automatic payment methods (bank transfer: 16.7%, credit card: 15.2%). The 1,071 electronic check churners represent **$84,289/month of revenue at risk**.

**Why it happens:**  
Electronic check is a manual payment method. Customers who pay manually are less financially "locked in" and also experience more friction (missed payments, billing confusion). The manual payment pattern is correlated with lower engagement and higher price sensitivity. Critically, it is also an **early warning signal**: customers who will churn tend to switch *away from* automatic payment before they cancel, making payment method a useful lead indicator in a churn prediction model.

**Recommended action:**  
Run an **auto-pay migration campaign** targeting electronic check customers:
- Offer a $5/month bill credit for 3 months in exchange for setting up bank transfer or credit card auto-pay.
- Automate a reminder workflow: customers who miss a payment and are on a month-to-month contract should receive a retention call within 72 hours.

Converting 30% of the 2,365 electronic check customers to auto-pay (based on similar industry campaigns) would remove approximately **710 customers** from the highest-risk payment segment. At a 45.3% churn rate vs a projected ~17% post-conversion, this prevents roughly **200 churns/month**, recovering **~$13,000/month** in revenue against a campaign cost of $710 × $15 = $10,650 — net positive in the first month.

---

## Summary Table

| Insight | Segment | Churn Rate | Monthly Revenue at Risk | Priority Action |
|---|---|---|---|---|
| 1. Contract type | Month-to-month | 42.7% | $120,847 | 6-month loyalty upgrade offer at tenure 3–6m |
| 2. Early tenure | 0–12 months | 47.4% | $68,954 | 3-touchpoint onboarding programme |
| 3. Fiber optic | Fiber optic internet | 41.9% | $114,300 | Priority complaint resolution + renewal anchoring |
| 4. Payment method | Electronic check | 45.3% | $84,289 | Auto-pay migration with bill credit incentive |

**Combined revenue at risk (overlap-adjusted estimate): ~$139,131/month**  
A retention programme targeting all four segments with a conservative 15% success rate would recover approximately **$20,000+/month** in recurring revenue.
