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

class BetExtractionDetails(BaseModel):
    bet_id: Optional[str] = None
    result: Optional[str] = None
    league: Optional[str] = None
    date: Optional[str] = None
    away_team: Optional[str] = None
    home_team: Optional[str] = None
    wager_team: Optional[str] = None
    bet_type: Optional[str] = None
    selection: Optional[str] = None
    odds: Optional[str] = None
    stake: Optional[str] = None
    payout: Optional[str] = None
    outcome: Optional[str] = Field(default=BetOutcome.WON)

    @classmethod
    def validate(cls, value):
        if value.get('bet_id') is None:
            value['bet_id'] = str(uuid.uuid4())
        return super().validate(value)

class BetDetails(BetExtractionDetails):
    bet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Generate a unique bet_id
    user_id: str = "Nate"
    upload_timestamp: Optional[str] = Field(default_factory=lambda: str(datetime.utcnow()))
    profit_loss: Optional[Decimal] = None

    @classmethod
    def validate(cls, value):
        if value.get('bet_id') is None:
            value['bet_id'] = str(uuid.uuid4())
        return super().validate(value)
    
class UserDetails(BaseModel):
    user_id: str
    bankroll: Decimal