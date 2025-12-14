#!/bin/bash
# Setup Binance same-exchange arbitrage trading pairs

echo "=========================================="
echo "Setting up Binance Same-Exchange Arbitrage"
echo "=========================================="
echo ""

API_URL="http://localhost:8000/api"
AUTH="admin:admin"

# Function to add trading pair
add_pair() {
    local symbol=$1
    local min_amount=${2:-0.001}
    
    echo "Adding pair: $symbol"
    response=$(curl -s -X POST -u "$AUTH" "$API_URL/tokens" \
        -H "Content-Type: application/json" \
        -d "{\"symbol\":\"$symbol\",\"min_trade_amount\":$min_amount,\"enabled\":true}")
    
    if echo "$response" | grep -q "success"; then
        echo "  ✓ Added: $symbol"
    else
        echo "  ✗ Failed: $symbol"
        echo "    Response: $response"
    fi
}

# Add common Binance pairs for triangular arbitrage
echo "Adding trading pairs..."
echo ""

# Core pairs for triangular arbitrage
add_pair "BTC/USDT" 0.001
add_pair "ETH/USDT" 0.001
add_pair "ETH/BTC" 0.001

# Additional popular pairs
add_pair "BNB/USDT" 0.01
add_pair "BNB/BTC" 0.01
add_pair "BNB/ETH" 0.01

# FDUSD pairs (Binance specific)
add_pair "BTC/FDUSD" 0.001
add_pair "ETH/FDUSD" 0.001

# More pairs for more opportunities
add_pair "SOL/USDT" 0.1
add_pair "ADA/USDT" 1.0
add_pair "DOT/USDT" 0.1
add_pair "LINK/USDT" 0.1

echo ""
echo "=========================================="
echo "Verifying pairs..."
echo "=========================================="

# Check configured pairs
pairs=$(curl -s "$API_URL/tokens/pairs")
pair_count=$(echo "$pairs" | grep -o '"symbol"' | wc -l)
echo "Total pairs configured: $pair_count"

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Restart the bot to pick up new pairs:"
echo "   curl -X POST -u admin:admin $API_URL/bot/stop"
echo "   sleep 5"
echo "   curl -X POST -u admin:admin $API_URL/bot/start"
echo ""
echo "2. Check bot status:"
echo "   curl $API_URL/bot/status | grep -o '\"symbols_monitored\":[0-9]*'"
echo ""
echo "3. Monitor opportunities:"
echo "   curl $API_URL/market/opportunities"
echo ""
echo "4. (Optional) Disable Galaswap if API errors persist:"
echo "   curl -X POST -u admin:admin $API_URL/exchanges/toggle \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"exchange_name\":\"galaswap\",\"enabled\":false}'"
echo ""

