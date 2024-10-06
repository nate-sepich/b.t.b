from datetime import datetime

class IngestionProvider:
    def parse_copy_paste_data(self, raw_text):
        print("Raw input:", raw_text)
        bets = []

        # Split the input text into lines, stripping extra spaces and blank lines
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        bet = {}

        # Iterate through each line and parse based on expected sequence of attributes
        for line in lines:
            # Determine the attribute based on the current state of `bet`
            if "bet_type" not in bet:
                # Bet type (Straight or Parlay) and Outcome (Win or Loss)
                if line.startswith("Straight") or line.startswith("Parlay"):
                    parts = line.split(" ")
                    if len(parts) >= 2:
                        bet["bet_type"] = parts[0]
                        bet["outcome"] = parts[1]
                        if len(parts) > 3 and parts[2] == "·":
                            bet["winnings"] = float(parts[3][1:])  # Extract winnings after "$"
                        else:
                            bet["winnings"] = 0.0
                    else:
                        continue  # Skip lines that don't have enough information
            elif "bet_description" not in bet:
                # Bet description
                bet["bet_description"] = line
            elif "bet_details" not in bet:
                # Bet details (e.g., Game Spread, Total Points, etc.)
                bet["bet_details"] = line
            elif "odds" not in bet:
                # Odds (e.g., -125, -110, etc.)
                try:
                    bet["odds"] = int(line)
                except ValueError:
                    continue  # Skip if odds are not in expected integer format
            elif "league" not in bet:
                # League or Final
                if "Final" in line:
                    parts = line.split("·")
                    if len(parts) > 1:
                        bet["league"] = parts[1].strip()
                    else:
                        bet["league"] = "Unknown"
            elif "away_team" not in bet:
                # Away team and score
                parts = line.rsplit(" ", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    bet["away_team"] = parts[0].replace("-logo", "").strip()  # Remove logo suffix if present
                    bet["away_score"] = int(parts[1])
            elif "home_team" not in bet:
                # Home team and score
                parts = line.rsplit(" ", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    bet["home_team"] = parts[0].replace("-logo", "").strip()  # Remove logo suffix if present
                    bet["home_score"] = int(parts[1])
            elif "bet_datetime" not in bet:
                # Date and time of the game
                try:
                    bet_date, bet_time = line.rsplit(" at ", 1)
                    bet_datetime = datetime.strptime(f"{bet_date} {bet_time}", "%b %d, %Y %I:%M %p")
                except ValueError:
                    continue
            elif "bet_datetime" not in bet:
                # Date and time of the game
                try:
                    bet_date, bet_time = line.rsplit(" at ", 1)
                    bet["bet_datetime"] = datetime.strptime(f"{bet_date} {bet_time}", "%b %d, %Y %I:%M %p")
                except ValueError:
                    continue  # Skip lines with incorrect date-time format
            elif "bet_amount" not in bet:
                if line.startswith("$"):
                    try:
                        bet["bet_amount"] = float(line[1:])
                    except ValueError:
                        continue
            elif "payout" not in bet:
                # Payout amount
                if line.startswith("$"):
                    try:
                        bet["payout"] = float(line[1:])
                    except ValueError:
                        continue
            elif "settled_date" not in bet:
                # Settlement date
                if line.startswith("Settled:"):
                    bet["settled_date"] = line.replace("Settled: ", "")
            elif "bet_id" not in bet:
                # Bet ID
                if line.startswith("ID:"):
                    bet["bet_id"] = line.replace("ID: ", "")
                    # When we have all attributes, add the bet to the list and reset for the next one
                    bets.append(bet)
                    bet = {}

        # Debugging: print parsed bets for inspection
        print("Parsed bets:", bets)

        return bets

