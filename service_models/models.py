import uuid
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum

class LLMRequestModel(BaseModel):
    extracted_text: str
    # output_json: dict
    
class LLMParsedDataResponse(BaseModel):
    parsed_data: dict


class BetOutcome(str, Enum):
    WON = 'WON'
    LOST = 'LOST'
    PUSH = 'PUSH'
    PENDING = 'PENDING'

class BetType(str, Enum):
    MONEYLINE = 'Moneyline'
    SPREAD = 'Spread'
    TOTAL = 'Totals'
    PROP = 'Prop'
    FUTURE = 'Future'
    OTHER = 'Other'

class BetDetails(BaseModel):
    user_id: str = "Nate"
    bet_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))  # Generate a unique bet_id
    upload_timestamp: Optional[str] = Field(default_factory=lambda: str(datetime.utcnow()))
    league: Optional[str] = None
    season: Optional[int] = None
    date: Optional[str] = None
    game_id: Optional[str] = None
    away_team: Optional[str] = None
    home_team: Optional[str] = None
    wager_team: Optional[str] = None
    bet_type: Optional[str] = None
    selection: Optional[str] = None
    odds: Optional[str] = None
    risk: Optional[str] = None
    to_win: Optional[str] = None
    payout: Optional[str] = None
    outcome: Optional[str] = Field(default=BetOutcome.WON)
    profit_loss: Optional[Decimal] = None

    
class UserDetails(BaseModel):
    user_id: str
    bankroll: Decimal