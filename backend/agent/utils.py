import re
from typing import List

def extract_tickers(query: str) -> List[str]:
    """
    Extracts stock tickers from a given query.
    Assumes tickers are 2-5 uppercase letters.
    """
    # Regex to pull 2 to 5 uppercase letter sequences.
    # Exclude common uppercase words if necessary, but this is a simplified approach.
    matches = re.findall(r'\b[A-Z]{2,5}\b', query)
    
    # Optional: Filter out common stop words that are 2-5 uppercase letters
    stop_words = {"AND", "OR", "THE", "IN", "ON", "OF", "TO", "A", "AN", "IS", "ARE", "VS"}
    
    tickers = []
    for match in matches:
        if match not in stop_words and match not in tickers:
            tickers.append(match)
            
    return tickers
