from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Google Flights Search Input Models
# ============================================================================

class MultiCityFlightSegment(BaseModel):
    departure_id: str = Field(
        description=(
            "Departure airport code or location identifier. "
            "Uses the same format as the main departure_id parameter."
        )
    )
    arrival_id: str = Field(
        description=(
            "Arrival airport code or location identifier. "
            "Uses the same format as the main arrival_id parameter. "
            "May include multiple comma-separated airports."
        )
    )
    date: str = Field(
        description=(
            "Flight date for this segment in YYYY-MM-DD format. "
            "Matches the format used by outbound_date."
        )
    )
    times: Optional[str] = Field(
        default=None,
        description=(
            "Optional time window for this segment. "
            "Uses the same comma-separated hour range format as outbound_times. "
            "Example: '8,18,9,23' for departure 08:00-18:00 and arrival 09:00–23:00."
        )
    )

class GoogleFlightsSearchParams(BaseModel):

    # --- Search Query ---
    type: Optional[Literal[1, 2, 3]] = Field(
        default=None,
        description="1=Round trip, 2=One way, 3=Multi-city. When set to 3, use multi_city_json to set the flight information."
    )

    departure_id: Optional[str] = Field(default=None, description="Departure airport code. It is an uppercase 3-letter IATA code. For example, CDG is Paris Charles de Gaulle Airport and AUS is Austin-Bergstrom International Airport. You can specify multiple departure airports by separating them with a comma. For example, CDG,ORY")
    arrival_id: Optional[str] = Field(default=None, description="Arrival airport code. It is an uppercase 3-letter IATA code. For example, HND is Tokyo Haneda Airport and PEK is Beijing Capital International Airport. You can specify multiple arrival airports by separating them with a comma. For example, HND,PEK")
    multi_city_json: Optional[List[MultiCityFlightSegment]] = None

    # --- Localization ---
    gl: Optional[str] = Field(default="ca", description="Geolocation of the user to use for the search. It is a 2-letter country code. For example, us is United States and fr is France.")
    hl: Optional[str] = Field(default="en", description="Language of the search results. It is a 2-letter language code. For example, en is English and fr is French.")
    currency: Optional[str] = Field(default="CAD", description="Currency to use for the prices. It is a 3-letter currency code. For example, USD is United States Dollar and EUR is Euro.")

    # --- Advanced Google Flights Parameters ---
    outbound_date: Optional[str] = Field(default=None, description="Outbound date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(default=None, description="Return date in YYYY-MM-DD format")
    
    # Following two are only available for https://serpapi.com/google-travel-explore-api
    # month: Optional[int] = Field(
    #     default=None,
    #     description=(
    #         "Month selector for flexible-date searches. "
    #         "Accepts values 1–12 (1=January, 12=December). "
    #         "A value of 0 means all months within the next six months are considered. "
    #         "Only months within the next six months from today are valid."
    #     )
    # )
    # travel_duration: Optional[Literal[1, 2, 3]] = Field(
    #     default=None,
    #     description=(
    #         "Trip duration for flexible-date searches. "
    #         "1=Weekend, 2=One week (default), 3=Two weeks."
    #     )
    # )

    travel_class: Optional[Literal[1, 2, 3, 4]] = Field(
        default=None,
        description="1=Economy, 2=Premium Economy, 3=Business, 4=First"
    ) 
    show_hidden: Optional[bool] = None
    exclude_basic: Optional[bool] = None
    deep_search: Optional[bool] = None # Set to true to enable deep search, which may yield better results but with a longer response time. Deep search results are identical to those found on Google Flights pages in the browser. 


    # --- Passengers ---
    adults: Optional[int] = None
    children: Optional[int] = None
    infants_in_seat: Optional[int] = None
    infants_on_lap: Optional[int] = None

    # --- Sorting ---
    sort_by: Optional[Literal[1, 2, 3, 4, 5, 6]] = Field(
        default=None,
        description="1=Top flights, 2=Price, 3=Departure, 4=Arrival, 5=Duration, 6=Emissions"
    )

    # --- Advanced Filters ---
    stops: Optional[Literal[0, 1, 2, 3]] = Field(default=None, description="0=any number of stops, 1=non-stop only, 2=1 stop or fewer, 3=2 stops or fewer")
    exclude_airlines: Optional[str] = None
    include_airlines: Optional[str] = None
    bags: Optional[int] = None
    max_price: Optional[int] = None
    outbound_times: Optional[str] = None
    return_times: Optional[str] = None
    emissions: Optional[Literal[1]] = None
    layover_duration: Optional[str] = None
    exclude_conns: Optional[str] = None
    max_duration: Optional[int] = None

    # --- Next Flights ---
    departure_token: Optional[str] = None

    # --- Booking ---
    booking_token: Optional[str] = None

    # --- SerpApi Parameters ---
    no_cache: Optional[bool] = None
    async_: Optional[bool] = Field(
        default=None,
        alias="async",
        description="Use async mode"
    )
    zero_trace: Optional[bool] = None
    output: Optional[Literal["json", "html"]] = None
    json_restrictor: Optional[str] = None
    
    # exclude_airlines and include_airlines parameters can't be used together.
    @model_validator(mode="after")
    def validate_airline_filters(self):
        if self.exclude_airlines and self.include_airlines:
            raise ValueError("exclude_airlines and include_airlines parameters cannot be used together.")
        return self

    @field_validator("departure_id", "arrival_id", mode="before")
    @classmethod
    def check_iata(cls, v):
        if v is None:
            return v
        if ',' not in v and (not v.isupper() or len(v) != 3):
            raise ValueError("departure_id and arrival_id must be IATA code - an uppercase 3-letter strings.")
        if ',' in v:
            codes = v.split(',')
            for code in codes:
                if not code.isupper() or len(code) != 3:
                    raise ValueError("Each IATA code in the comma-separated list must be an uppercase 3-letter string.")
        return v.upper()


# ============================================================================
# Google Flights Response Models
# ============================================================================
class DepartureAirportInfo(BaseModel):
    name: str = Field(description="airport name")
    id: str = Field(description="airport IATA code")
    time: str = Field(description="departure time")

class ArrivalAirportInfo(BaseModel):
    name: str = Field(description="airport name")
    id: str = Field(description="airport IATA code")
    time: str = Field(description="arrival time")

class FlightSegment(BaseModel):
    """Represents a single flight segment within a flight itinerary."""
    departure_airport: DepartureAirportInfo
    arrival_airport: ArrivalAirportInfo
    duration: int  # in minutes
    airplane: str | None = None
    airline: str
    airline_logo: Optional[str] = None
    flight_number: str
    travel_class: str
    legroom: Optional[str] = None
    extensions: Optional[List[str]] = None
    often_delayed: bool = Field(default=False, alias="often_delayed_by_over_30_min") # where to get this info?

    def to_summary(self) -> Dict[str, Any]:
        """Convert flight segment to a summary dictionary."""
        return self.model_dump(exclude={"airplane", "airline_logo", "flight_number", "extensions"})

class Layover(BaseModel):
    """Represents a layover during a trip."""
    duration: int  # in minutes
    airport_id: str = Field(alias="id")
    airport_name: str = Field(alias="name")
    overnight: bool = Field(default=False)


class FlightOption(BaseModel):
    """Represents a complete flight option (itinerary)."""
    flights: List[FlightSegment]
    layovers: Optional[List[Layover]] = None
    total_duration: int  # in minutes
    price: int
    carbon_emissions: Optional[Dict[str, Any]] = None
    type: str  # e.g., "Round trip", "One way"
    airline_logo: Optional[str] = None
    departure_token: Optional[str] = None

    def to_summary(self) -> Dict[str, Any]:
        """Convert flight option to a summary for LLM analysis."""
        if not self.flights:
            return {}

        # Extract key info from flights
        first_flight = self.flights[0]
        last_flight = self.flights[-1]

        # Parse dates from flight times
        departure_time = first_flight.departure_airport.time
        arrival_time = last_flight.arrival_airport.time

        # Collect airlines
        airlines = list(set(f.airline for f in self.flights))

        # Build layover info
        layover_info = []
        if self.layovers:
            for layover in self.layovers:
                layover_info.append(
                    f"{layover.airport_name} ({layover.airport_id}): {layover.duration // 60}h {layover.duration % 60}m"
                    + (" (overnight)" if layover.overnight else "")
                )

        # Calculate number of stops
        num_stops = len(self.flights) - 1

        return {
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "departure_airport": first_flight.departure_airport.id,
            "arrival_airport": last_flight.arrival_airport.id,
            "total_price": self.price,
            "total_duration_minutes": self.total_duration,
            "total_duration_hours": f"{self.total_duration // 60}h {self.total_duration % 60}m",
            "num_stops": num_stops,
            "airlines": airlines,
            "trip_type": self.type,
            "flight_segments": [
                f.to_summary()
                for f in self.flights
            ],
            "layovers": layover_info
        }


class Airport(BaseModel):
    """Airport information."""
    id: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None


class GoogleFlightsSearchResponse(BaseModel):
    """Complete Google Flights search response from SerpAPI."""
    best_flights: List[FlightOption] = Field(default_factory=list)
    other_flights: List[FlightOption] = Field(default_factory=list)
    airports: Optional[List[Dict[str, Any]]] = None
    search_parameters: Optional[Dict[str, Any]] = None
    price_insights: Optional[Dict[str, Any]] = None

    def to_summary(self, top_n: int = 5) -> Dict[str, Any]:
        """
        Convert response to a summary for LLM analysis.
        
        Args:
            top_n: Number of top flight options to include in summary.
        
        Returns:
            Summarized data suitable for LLM analysis.
        """
        # Combine best and other flights
        all_flights = self.best_flights + self.other_flights

        # Take top N by price
        top_flights = sorted(all_flights, key=lambda f: f.price)[:top_n]

        # Convert each flight to summary
        flight_summaries = [
            flight.to_summary()
            for flight in top_flights
        ]

        # Get search context
        search_context = {}
        if self.search_parameters:
            search_context = {
                "departure": self.search_parameters.get("departure_id"),
                "arrival": self.search_parameters.get("arrival_id"),
                "outbound_date": self.search_parameters.get("outbound_date"),
                "return_date": self.search_parameters.get("return_date"),
                "currency": self.search_parameters.get("currency"),
            }

        return {
            "search_context": search_context,
            "flight_options": flight_summaries,
            "total_options_available": len(all_flights),
            "price_range": {
                "min": min(f.price for f in all_flights) if all_flights else None,
                "max": max(f.price for f in all_flights) if all_flights else None,
            } if all_flights else {},
        }