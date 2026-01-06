"""
FlexiFlight Requirement Interpreter

Interprets natural language flight requirements and converts them into
structured GoogleFlightsSearchParams objects for SerpAPI consumption.
"""

import json
import logging
import re
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import ValidationError

from llm import call_vllm
from models.models import GoogleFlightsSearchParams, MultiCityFlightSegment

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Common IATA airport codes
# Cities with multiple airports are mapped to comma-separated codes
COMMON_AIRPORTS = {
  "Toronto": "YYZ,YTZ",
  "Montreal": "YUL,YHU",
  "Vancouver": "YVR,YXX",
  "Calgary": "YYC",
  "Ottawa": "YOW",
  "Edmonton": "YEG",

  "New York": "JFK,LGA,EWR",
  "Los Angeles": "LAX,BUR,SNA,LGB,ONT",
  "San Francisco": "SFO,OAK,SJC",
  "Chicago": "ORD,MDW",
  "Washington DC": "IAD,DCA,BWI",
  "Miami": "MIA,FLL,PBI",
  "Dallas": "DFW,DAL",
  "Houston": "IAH,HOU",
  "Boston": "BOS",
  "Seattle": "SEA",

  "London": "LHR,LGW,STN,LTN,LCY,SEN",
  "Paris": "CDG,ORY",
  "Rome": "FCO,CIA",
  "Milan": "MXP,LIN,BGY",
  "Berlin": "BER",
  "Amsterdam": "AMS",
  "Frankfurt": "FRA",
  "Munich": "MUC",
  "Madrid": "MAD",
  "Barcelona": "BCN",

  "Beijing": "PEK,PKX",
  "Shanghai": "PVG,SHA",
  "Guangzhou": "CAN",
  "Shenzhen": "SZX",
  "Chengdu": "CTU,TIA",
  "Chongqing": "CKG",
  "Wuhan": "WUH",
  "Hong Kong": "HKG",
  "Macau": "MFM",
  "Taipei": "TPE,TSA"
}


def validate_iata_code(code: str) -> bool:
    """Validate that code is a 3-letter IATA code (single code only)."""
    if not isinstance(code, str):
        return False
    code = code.upper().strip()
    return len(code) == 3 and code.isalpha()


def city_to_iata(city_name: str) -> Optional[str]:
    """
    Convert city name to IATA code(s) using lookup table or LLM.
    Returns single code or comma-separated codes for cities with multiple airports.
    """
    # Normalize input
    city_lower = city_name.lower().strip()
    
    # Check common airports lookup
    if city_lower in COMMON_AIRPORTS:
        return COMMON_AIRPORTS[city_lower]
    
    # Try fuzzy matching against known airports
    for city_key, iata in COMMON_AIRPORTS.items():
        if city_key in city_lower or city_lower in city_key:
            return iata
    
    # Fall back to LLM if not found
    try:
        prompt = f"""Convert this city or airport name to IATA code(s).
If the city has multiple major airports, return them all separated by commas.
City/Airport: {city_name}

Return ONLY IATA codes (uppercase, separated by comma if multiple), nothing else.
Examples:
- "Paris" -> CDG,ORY
- "New York" -> JFK,LGA,EWR
- "LAX" -> LAX
- "Tokyo" -> NRT,HND
- "London" -> LHR,LGW,STN,LCY,LTN

If you cannot determine a valid IATA code, return "UNKNOWN"."""
        
        response = call_vllm([{"role": "user", "content": prompt}])
        codes = response.strip().upper()
        
        # Validate all codes in the response
        if ',' in codes:
            code_list = [c.strip() for c in codes.split(',')]
            # Validate each code
            for code in code_list:
                if not validate_iata_code(code):
                    return None
            return ','.join(code_list)
        else:
            if validate_iata_code(codes):
                return codes
    except Exception as e:
        logger.warning(f"Failed to convert city to IATA with LLM: {e}")
    
    return None


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats and return YYYY-MM-DD format.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Common formats
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Try LLM parsing
    try:
        prompt = f"""Parse this date description to YYYY-MM-DD format.
Date description: {date_str}
Today's date: {datetime.now().strftime("%Y-%m-%d")}

Return ONLY the date in YYYY-MM-DD format."""
        
        response = call_vllm([{"role": "user", "content": prompt}])
        parsed = response.strip()
        
        if re.match(r'^\d{4}-\d{2}-\d{2}$', parsed):
            return parsed
    except Exception as e:
        logger.warning(f"Failed to parse date with LLM: {e}")
    
    return None


def extract_multi_city_segments(intent_data: Dict[str, Any]) -> Optional[List[MultiCityFlightSegment]]:
    """
    Extract multi-city flight segments from parsed intent.
    Handles cities with multiple airports by returning comma-separated IATA codes.
    """
    segments_data = intent_data.get("multi_city_segments")
    if not segments_data or not isinstance(segments_data, list):
        return None
    
    segments = []
    for seg in segments_data:
        try:
            # Convert cities to IATA codes (may return multiple separated by comma)
            dep_iata = city_to_iata(seg.get("departure", ""))
            arr_iata = city_to_iata(seg.get("arrival", ""))
            date = parse_date(seg.get("date", ""))
            times = seg.get("times")
            
            if not dep_iata or not arr_iata or not date:
                logger.warning(f"Skipping segment due to missing data: {seg}")
                continue
            
            segment = MultiCityFlightSegment(
                departure_id=dep_iata,
                arrival_id=arr_iata,
                date=date,
                times=times
            )
            segments.append(segment)
        except ValidationError as e:
            logger.warning(f"Failed to create segment: {e}")
            continue
    
    return segments if segments else None


def build_search_params_from_intent(intent_data: Dict[str, Any]) -> List[GoogleFlightsSearchParams]:
    """
    Build GoogleFlightsSearchParams objects from parsed intent data.
    """
    params_list = []
    
    try:
        flight_type = intent_data.get("flight_type", "one_way").lower()
        
        # Handle multi-city flights
        if flight_type == "multi_city":
            # TODO: Implement multi-city handling
            segments = extract_multi_city_segments(intent_data)
            if not segments:
                logger.error("Multi-city flight specified but no valid segments found")
                return []
            
            params = GoogleFlightsSearchParams(
                type=3,  # Multi-city
                departure_id=None,
                arrival_id=None,
                outbound_date=None,
                return_date=None,
                multi_city_json=segments,
                adults=intent_data.get("adults", 1),
                children=intent_data.get("children", 0),
                infants_in_seat=intent_data.get("infants_in_seat", 0),
                infants_on_lap=intent_data.get("infants_on_lap", 0),
                travel_class=intent_data.get("travel_class"),
                stops=intent_data.get("stops"),
                gl=intent_data.get("gl", "ca"),
                hl=intent_data.get("hl", "en"),
                currency=intent_data.get("currency", "CAD"),
            )
            params_list.append(params)
        
        else:  # One-way or round-trip
            departure_city = intent_data.get("departure_city")
            arrival_city = intent_data.get("arrival_city")
            
            if not departure_city or not arrival_city:
                logger.error("Departure and arrival cities are required")
                return []
            
            departure_iata = city_to_iata(departure_city)
            arrival_iata = city_to_iata(arrival_city)
            
            if not departure_iata or not arrival_iata:
                logger.error(f"Could not convert cities to IATA codes. Dep: {departure_iata}, Arr: {arrival_iata}")
                return []
            
            outbound_date = parse_date(intent_data.get("outbound_date", ""))
            return_date = parse_date(intent_data.get("return_date", "")) if flight_type == "round_trip" else None
            
            if not outbound_date:
                logger.error("Outbound date is required")
                return []
            
            # Determine flight type code
            type_code = 1 if flight_type == "round_trip" else 2
            
            # Create base parameters
            params = GoogleFlightsSearchParams(
                type=type_code,
                departure_id=departure_iata,
                arrival_id=arrival_iata,
                outbound_date=outbound_date,
                return_date=return_date,
                multi_city_json=None,
                adults=intent_data.get("adults", 1),
                children=intent_data.get("children", 0),
                infants_in_seat=intent_data.get("infants_in_seat", 0),
                infants_on_lap=intent_data.get("infants_on_lap", 0),
                travel_class=intent_data.get("travel_class"),
                stops=intent_data.get("stops"),
                gl=intent_data.get("gl", "ca"),
                hl=intent_data.get("hl", "en"),
                currency=intent_data.get("currency", "CAD"),
                exclude_airlines=intent_data.get("exclude_airlines"),
                include_airlines=intent_data.get("include_airlines"),
                max_price=intent_data.get("max_price"),
                bags=intent_data.get("bags"),
                outbound_times=intent_data.get("outbound_times"),
                return_times=intent_data.get("return_times"),
            )
            params_list.append(params)
            
            # Generate alternative search options if flexible dates
            if intent_data.get("flexible_dates"):
                try:
                    outbound_dt = datetime.strptime(outbound_date, "%Y-%m-%d")
                    
                    # Generate ±1 day variations
                    for day_offset in [-1, 1]:
                        alt_outbound = (outbound_dt + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                        alt_return = None
                        
                        if return_date:
                            return_dt = datetime.strptime(return_date, "%Y-%m-%d")
                            alt_return = (return_dt + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                        
                        alt_params = GoogleFlightsSearchParams(
                            type=type_code,
                            departure_id=departure_iata,
                            arrival_id=arrival_iata,
                            outbound_date=alt_outbound,
                            return_date=alt_return,
                            multi_city_json=None,
                            adults=intent_data.get("adults", 1),
                            children=intent_data.get("children", 0),
                            infants_in_seat=intent_data.get("infants_in_seat", 0),
                            infants_on_lap=intent_data.get("infants_on_lap", 0),
                            travel_class=intent_data.get("travel_class"),
                            stops=intent_data.get("stops"),
                            gl=intent_data.get("gl", "ca"),
                            hl=intent_data.get("hl", "en"),
                            currency=intent_data.get("currency", "CAD"),
                            exclude_airlines=intent_data.get("exclude_airlines"),
                            include_airlines=intent_data.get("include_airlines"),
                            max_price=intent_data.get("max_price"),
                            bags=intent_data.get("bags"),
                            outbound_times=intent_data.get("outbound_times"),
                            return_times=intent_data.get("return_times"),
                        )
                        params_list.append(alt_params)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not generate flexible date variations: {e}")
    
    except Exception as e:
        logger.error(f"Error building search parameters: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    return params_list


def parse_user_input(user_input: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Parse natural language user input using LLM to extract flight requirements.
    
    Returns:
        Tuple of (parsed_intent, errors)
    """
    errors = []
    
    try:
        prompt = f"""You are a flight search intent parser. Analyze the user's flight request and extract the following information.

User Request: {user_input}

IMPORTANT NOTES:
- For cities with multiple airports (e.g., New York, London, Paris), list ALL major airports separated by commas
- Examples: "New York" -> "JFK,LGA,EWR", "London" -> "LHR,LGW,STN", "Paris" -> "CDG,ORY"
- This allows searching across all airports in a city for better options

Please provide the output as a valid JSON object with ONLY these fields (include all fields, use null for missing):
- flight_type: "one_way", "round_trip", or "multi_city" (required)
- departure_city: city name or airport code(s) for departure, separated by comma if multiple (required for one_way/round_trip)
- arrival_city: city name or airport code(s) for arrival, separated by comma if multiple (required for one_way/round_trip)
- outbound_date: date in YYYY-MM-DD format or relative date like "tomorrow", "next Monday" (required)
- return_date: date in YYYY-MM-DD format (only for round_trip)
- multi_city_segments: list of segments ONLY for multi_city flights. Each segment has: departure, arrival, date, times (optional)
- adults: number of adults (default 1)
- children: number of children (default 0)
- infants_in_seat: number of infants in seat (default 0)
- infants_on_lap: number of infants on lap (default 0)
- travel_class: 1=Economy, 2=Premium Economy, 3=Business, 4=First (null if not specified)
- flexible_dates: boolean (true if user mentions flexible dates)
- stops: 0=any, 1=nonstop, 2=1 stop or fewer, 3=2 stops or fewer (null if not specified)
- max_price: integer price limit in local currency (null if not specified)
- bags: number of carry-on bags (null if not specified)
- exclude_airlines: comma-separated airline codes to exclude (null if not specified)
- include_airlines: comma-separated airline codes to include (null if not specified)
- outbound_times: time range like "8,18" for 8am-6pm departure (null if not specified)
- return_times: time range for return flight (null if not specified)
- gl: 2-letter country code (default "ca")
- hl: 2-letter language code (default "en")
- currency: 3-letter currency code (default "CAD")

Return ONLY valid JSON without any markdown, explanation, or extra text.
Example output:
{{"flight_type": "round_trip", "departure_city": "JFK,LGA,EWR", "arrival_city": "CDG,ORY", "outbound_date": "2025-06-15", "return_date": "2025-06-22", "adults": 2, "children": 0, "infants_in_seat": 0, "infants_on_lap": 0, "travel_class": null, "flexible_dates": false, "stops": null, "max_price": null, "bags": null, "exclude_airlines": null, "include_airlines": null, "outbound_times": null, "return_times": null, "multi_city_segments": null, "gl": "ca", "hl": "en", "currency": "CAD"}}"""
        
        response = call_vllm([{"role": "user", "content": prompt}], enable_thinking=False)
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            errors.append("Failed to extract JSON from LLM response")
            return None, errors
        
        intent_data = json.loads(json_match.group(0))
        return intent_data, errors
        
    except json.JSONDecodeError as e:
        errors.append(f"Failed to parse LLM response as JSON: {str(e)}")
        return None, errors
    except Exception as e:
        errors.append(f"Error parsing user input: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, errors


def interpret_user_requirements(user_input: str) -> Tuple[List[GoogleFlightsSearchParams], List[str]]:
    """
    Main function to interpret user flight requirements.
    
    Args:
        user_input: Natural language user flight request
        
    Returns:
        Tuple of (search_params_list, errors)
        - search_params_list: List of validated GoogleFlightsSearchParams objects
        - errors: List of any errors or warnings encountered
    """
    all_errors = []
    
    # Step 1: Parse user input with LLM
    intent_data, parse_errors = parse_user_input(user_input)
    all_errors.extend(parse_errors)
    
    if not intent_data:
        all_errors.append("Failed to parse user requirements")
        return [], all_errors
    
    # Step 2: Build flight search payload from intent and validate the payload
    search_params_list = build_search_params_from_intent(intent_data)

    return search_params_list, all_errors
