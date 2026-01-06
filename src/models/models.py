from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator, model_validator


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