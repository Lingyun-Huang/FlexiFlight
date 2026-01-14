"""
Integration example showing how to use analyze_flights in the FlexiFlight workflow.

This example demonstrates the complete flow:
1. Parse user requirements → GoogleFlightsSearchParams
2. Search flights using SerpAPI
3. Analyze results with LLM using the new analyze_flights tool
4. Display formatted recommendations to user
"""

import sys
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.requirement_interpreter import interpret_user_requirements
from tools.search_flights import search_google_flights
from tools.analyze_flights import analyze_flights, format_analysis_for_display


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def main():
    """
    Complete workflow: interpret requirements → search → analyze → recommend.
    """
    # Example user request
    user_request = "I want to fly round trip from Ottawa to Beijing from May 25 to June 12, 2026."
    
    logger.info("\n" + "=" * 80)
    logger.info("FLEXIFLIGHT FLIGHT   ANALYSIS WORKFLOW")
    logger.info("=" * 80)
    logger.info(f"\nUser Request: {user_request}\n")
    
    try:
        # Step 1: Interpret user requirements
        logger.info("Step 1: Interpreting user requirements...")
        search_params_list, errors = interpret_user_requirements(user_request)
        
        if errors:
            logger.warning(f"Warnings: {errors}")
        
        if not search_params_list:
            logger.error("Could not generate search parameters")
            return 1

        # Use first search option
        search_params = search_params_list[0]
        logger.info(f"Generated search parameters: {search_params.model_dump(exclude_none=True)}")
        
        # Step 2: Search flights
        logger.info("\nStep 2: Searching flights via SerpAPI...")
        flight_response = search_google_flights(search_params)
        logger.info(f"Found {len(flight_response.get('best_flights', []))} best flight options")
        
        # Step 3: Analyze with LLM
        logger.info("\nStep 3: Analyzing flight options with LLM...")
        analysis = analyze_flights(
            flight_response,
            top_n=5,
            holidays=["2026-05-25"],  # optional
        )
        
        # Step 4: Display results
        logger.info("\nStep 4: Displaying recommendations...\n")
        formatted_output = format_analysis_for_display(analysis)
        logger.info(formatted_output)
        
        # Save detailed analysis
        # output_file = "/tmp/flight_analysis_result.json"
        # with open(output_file, "w") as f:
        #     json.dump(analysis, f, indent=2)
        # logger.info(f"\nDetailed analysis saved to: {output_file}")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Error in workflow: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
