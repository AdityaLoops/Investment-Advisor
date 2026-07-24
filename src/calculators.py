def compound_interest(principal, rate, years):
    """Calculate final amount using compound interest formula."""
    final_amount = principal * (1 + rate) ** years
    return final_amount


def recommend_best(principal, years, options):
    """Compare multiple investment options and return the best one."""
    results = {}
    for name, rate in options.items():
        results[name] = compound_interest(principal, rate, years)
    
    best = max(results, key=results.get)
    return results, best

def recommend_fund(risk_return_df, years, penalty, risk_column='min', n=1):
    if not (0<=penalty <=2):
        print("Please enter a valid penalty range")
        return None
    subset = risk_return_df[risk_return_df['window_years'] == years].copy()
    subset['score'] = subset['mean'] - (penalty * subset[risk_column].apply(lambda x: max(-x,0)))

    top_results = subset.sort_values('score', ascending=False).head(n)

    print(f"Top {n} fund(s) recommened for {years} years at penalty weight {penalty} (risk measure: {risk_column}):\n")
    for rank, (_, row) in enumerate(top_results.iterrows(), start=1):
        print(f"  #{rank}: {row['fund']}")
        print(f"      Expected Cagr={row['mean']:.4f} ")
        print(f"      Worst Case Cagr return ({risk_column})={row[risk_column]:.4f}")
        print(f"      Score= {row['score']:.4f}\n")

    return top_results[['fund', 'mean', 'score', risk_column, 'sentiment_score']].reset_index(drop=True)

def advise_investment(risk_return_df, principal, years, penalty, risk_column='min', n=1):
    top_results = recommend_fund(risk_return_df, years, penalty, risk_column, n)
    if top_results is None:
        return None

    print(f"\nProjected value of Rs{principal} over {years} years, per recommended fund:")
    for _, row in top_results.iterrows():
        best_case = compound_interest(principal, row['mean'], years)
        worst_case = compound_interest(principal, row[risk_column], years)
        balanced = (best_case + worst_case) / 2

        print(f"  {row['fund']}:")
        print(f"      Balanced estimate:      approx Rs{balanced:.2f}")
        print(f"      Best case (mean):       approx Rs{best_case:.2f}")
        print(f"      Worst case ({risk_column}):   approx Rs{worst_case:.2f}")

    return top_results


def advise_investment_web(risk_return_df, principal, years, penalty,
                          risk_column='min', n=1):
    """
    Returns the top recommended funds in a format suitable for the web frontend.
    """

    top_results = recommend_fund(
        risk_return_df,
        years,
        penalty,
        risk_column,
        n
    )

    if top_results is None:
        return None

    recommendations = []

    for _, row in top_results.iterrows():

        best_case = compound_interest(principal, row["mean"], years)
        worst_case = compound_interest(principal, row[risk_column], years)
        balanced = (best_case + worst_case) / 2

        recommendations.append({
            "fund": row["fund"],
            "expected_cagr": round(row["mean"] * 100, 2),          # %
            "worst_case_cagr": round(row[risk_column] * 100, 2),   # %
            "score": round(row["score"], 4),
            "balanced_value": round(balanced, 2),
            "best_case_value": round(best_case, 2),
            "worst_case_value": round(worst_case, 2),
            "sentiment_score": round(row["sentiment_score"], 4),
            "sentiment_label": sentiment_label(row["sentiment_score"])
        })

    return recommendations
def sentiment_label(score):
    if score >= 0.15:
        return "Very Positive"
    elif score >= 0.05:
        return "Positive"
    elif score > -0.05:
        return "Neutral"
    elif score > -0.15:
        return "Negative"
    else:
        return "Very Negative"