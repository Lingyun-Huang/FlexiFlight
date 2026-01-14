"""
Tool to analyze Google Flights search responses and provide LLM-powered insights.

This tool:
1. Parses the SerpAPI Google Flights response
2. Extracts summaries of top flight options
3. Uses an LLM to compare options and provide trade-off analysis
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from models.serp import GoogleFlightsSearchResponse
from clients.openai_llm import call_vllm


logger = logging.getLogger(__name__)


def _is_weekend_or_holiday(date_str: str, holidays: Optional[List[str]] = None) -> tuple[bool, str]:
    """
    Check if a date is a weekend or public holiday.
    
    Args:
        date_str: Date string in YYYY-MM-DD format.
        holidays: List of holiday dates in YYYY-MM-DD format.
    
    Returns:
        Tuple of (is_weekend_or_holiday, reason_string).
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = date.weekday()  # 0=Monday, 6=Sunday
        
        if weekday >= 5:  # Saturday or Sunday
            day_name = "Saturday" if weekday == 5 else "Sunday"
            return True, f"{day_name}"
        
        if holidays and date_str in holidays:
            return True, "Public Holiday"
        
        return False, ""
    except (ValueError, TypeError):
        return False, ""


def _count_weekend_days(start_date_str: str, end_date_str: str, holidays: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Count weekend days and holidays within a date range.
    
    Args:
        start_date_str: Start date in YYYY-MM-DD format.
        end_date_str: End date in YYYY-MM-DD format.
        holidays: List of holiday dates in YYYY-MM-DD format.
    
    Returns:
        Dict with weekend/holiday counts.
    """
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        weekend_count = 0
        holiday_count = 0
        current = start
        
        while current <= end:
            if current.weekday() >= 5:  # Weekend
                weekend_count += 1
            elif holidays and current.strftime("%Y-%m-%d") in holidays:
                holiday_count += 1
            current += timedelta(days=1)
        
        trip_days = (end - start).days + 1
        
        return {
            "trip_days": trip_days,
            "weekend_days": weekend_count,
            "holiday_days": holiday_count,
            "weekday_days": trip_days - weekend_count - holiday_count,
        }
    except (ValueError, TypeError):
        return {"trip_days": 0, "weekend_days": 0, "holiday_days": 0, "weekday_days": 0}


def analyze_flights(
    response_data: Dict[str, Any],
    top_n: int = 5,
    holidays: Optional[List[str]] = None,
    model: str = "Qwen/Qwen3-1.7B",
) -> Dict[str, Any]:
    """
    Analyze Google Flights search response and provide LLM-powered comparison.
    
    This function:
    1. Parses the SerpAPI response into a GoogleFlightsSearchResponse model
    2. Extracts summaries of top flight options
    3. Uses an LLM to analyze and compare the options
    4. Returns structured insights with trade-offs and recommendations
    
    Args:
        response_data: Raw SerpAPI Google Flights response as dict.
        top_n: Number of top options to include in analysis (default 5).
        holidays: Optional list of public holidays in YYYY-MM-DD format.
        model: LLM model to use for analysis.
    
    Returns:
        Dict with analyzed flight options and LLM-powered insights.
    """
    try:
        # Parse response
        logger.info("Parsing Google Flights response...")
        search_response = GoogleFlightsSearchResponse(**response_data)
        
        # Generate summary
        logger.info(f"Generating summary for top {top_n} flights...")
        summary = search_response.to_summary(top_n=top_n)
        
        # Enrich with weekend/holiday info
        search_context = summary.get("search_context", {})
        # if search_context.get("outbound_date") and search_context.get("return_date"):
        #     trip_stats = _count_weekend_days(
        #         search_context["outbound_date"],
        #         search_context["return_date"],
        #         holidays,
        #     )
        #     summary["trip_statistics"] = trip_stats
        
        logger.info("Sending flight options to LLM for analysis...")

        # Prepare prompt for LLM
        flights_json = json.dumps(summary["flight_options"], indent=2)
        
        prompt = f"""Analyze the following flight options and provide a structured comparison. 
For each option, explain:
- Why it's a good choice (pros)
- Trade-offs or drawbacks (cons)
- Overall recommendation

Consider:
- Number of stops and layover times (prefer fewer stops and shorter layovers)
- Total cost (prefer lower prices)
- Total duration
- Airline reputation (if known, prefer major carriers)
- Overnight layovers (try to avoid)
- Flight delay risks (if marked as "often_delayed")
- Travel convenience

Flight Options:
{flights_json}

Provide your analysis in JSON format with this structure:
{{
    "options": [
        {{
            "option_index": 0,
            "pros": ["list of advantages"],
            "cons": ["list of disadvantages"],
            "trade_offs": "explanation of key trade-offs",
            "recommendation_score": "HIGH/MEDIUM/LOW with brief explanation"
        }}
    ],
    "best_option": {{"index": N, "reason": "explanation"}},
    "general_insights": ["insight1", "insight2", ...]
}}"""
        
        # Call LLM
        messages = [
            {
                "role": "system",
                "content": "You are a travel expert specializing in flight comparison and recommendation. Analyze flight options to help users make informed decisions.",
            },
            {"role": "user", "content": prompt},
        ]
        
        llm_analysis = call_vllm(messages, model=model)
        logger.debug(f"LLM Response: {llm_analysis}")
        
        # Parse LLM response
        try:
            analysis_json = json.loads(llm_analysis)
        except json.JSONDecodeError:
            logger.warning("Could not parse LLM response as JSON, returning raw response")
            analysis_json = {"raw_analysis": llm_analysis}
        
        # Combine results
        result = {
            "search_context": summary.get("search_context"),
            "trip_statistics": summary.get("trip_statistics"),
            "price_range": summary.get("price_range"),
            "flight_options": summary["flight_options"],
            "llm_analysis": analysis_json,
        }
        
        return result
    
    except Exception as e:
        logger.exception(f"Error analyzing flights: {e}")
        raise


def format_analysis_for_display(analysis: Dict[str, Any]) -> str:
    """
    Format the analysis results for user display.
    
    Args:
        analysis: Analysis result from analyze_flights().
    
    Returns:
        Formatted string for display.
    """
    output = []
    
    # Header
    context = analysis.get("search_context", {})
    output.append("=" * 80)
    output.append("FLIGHT ANALYSIS RESULTS")
    output.append("=" * 80)
    
    if context:
        output.append(f"\nRoute: {context.get('departure')} → {context.get('arrival')}")
        output.append(f"Dates: {context.get('outbound_date')} to {context.get('return_date')}")
        output.append(f"Currency: {context.get('currency')}")
    
    # Price range
    price_range = analysis.get("price_range", {})
    if price_range:
        output.append(f"\nPrice Range: ${price_range.get('min')} - ${price_range.get('max')}")
    
    # Trip statistics
    trip_stats = analysis.get("trip_statistics", {})
    if trip_stats:
        output.append(f"\nTrip Statistics:")
        output.append(f"  - Total Days: {trip_stats.get('trip_days')}")
        output.append(f"  - Weekend Days: {trip_stats.get('weekend_days')}")
        output.append(f"  - Weekday Days: {trip_stats.get('weekday_days')}")
    
    output.append("\n" + "=" * 80)
    output.append("FLIGHT OPTIONS")
    output.append("=" * 80)
    
    # Flight options
    for idx, flight in enumerate(analysis.get("flight_options", []), 1):
        output.append(f"\n[Option {idx}]")
        output.append(f"  Price: ${flight.get('total_price')}")
        output.append(f"  Duration: {flight.get('total_duration_hours')}")
        output.append(f"  Route: {flight.get('departure_airport')} → {flight.get('arrival_airport')}")
        
        num_stops = flight.get('num_stops', 0)
        stops_str = "Non-stop" if num_stops == 0 else f"{num_stops} stop(s)"
        output.append(f"  Stops: {num_stops} ({stops_str})")
        output.append(f"  Airlines: {', '.join(flight.get('airlines', []))}")
        output.append(f"  Trip Type: {flight.get('trip_type')}")
        
        if flight.get('layovers'):
            output.append(f"  Layovers:")
            for layover in flight['layovers']:
                output.append(f"    - {layover}")
    
    # LLM Analysis
    llm_analysis = analysis.get("llm_analysis", {})
    if llm_analysis:
        output.append("\n" + "=" * 80)
        output.append("ANALYSIS & RECOMMENDATIONS")
        output.append("=" * 80)
        
        best_option = llm_analysis.get("best_option", {})
        if best_option:
            output.append(f"\n✓ Best Overall Option: Option {best_option.get('index', 'N/A') + 1}")
            output.append(f"  Reason: {best_option.get('reason', 'N/A')}")
        
        insights = llm_analysis.get("general_insights", [])
        if insights:
            output.append(f"\nKey Insights:")
            for insight in insights:
                output.append(f"  • {insight}")
        
        options_analysis = llm_analysis.get("options", [])
        if options_analysis:
            output.append(f"\nDetailed Option Analysis:")
            for opt in options_analysis:
                opt_idx = opt.get("option_index", "N/A")
                output.append(f"\n  Option {opt_idx + 1}:")
                
                score = opt.get("recommendation_score", "N/A")
                output.append(f"    Recommendation: {score}")
                
                pros = opt.get("pros", [])
                if pros:
                    output.append(f"    Pros:")
                    for pro in pros:
                        output.append(f"      + {pro}")
                
                cons = opt.get("cons", [])
                if cons:
                    output.append(f"    Cons:")
                    for con in cons:
                        output.append(f"      - {con}")
                
                trade_offs = opt.get("trade_offs", "")
                if trade_offs:
                    output.append(f"    Trade-offs: {trade_offs}")
    
    output.append("\n" + "=" * 80)
    
    return "\n".join(output)
