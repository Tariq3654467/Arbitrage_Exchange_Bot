#!/bin/bash
# Test Galaswap API with correct object format

echo "Testing Galaswap API with correct format..."
echo ""

# Test with object format (what the API expects)
curl -X POST https://api-galaswap.gala.com/v1/FetchAvailableTokenSwaps \
  -H "Content-Type: application/json" \
  -d '{
    "offeredTokenClass": {
      "collection": "GUSDT",
      "category": "Unit",
      "type": "none",
      "additionalKey": "none"
    },
    "wantedTokenClass": {
      "collection": "GALA",
      "category": "Unit",
      "type": "none",
      "additionalKey": "none"
    }
  }' \
  -v

echo ""
echo ""
echo "If this works, the code should also work since it uses the same format."

