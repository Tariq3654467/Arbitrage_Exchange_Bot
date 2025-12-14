#!/bin/bash
# Quick diagnostic script to check why bot isn't trading

echo "=========================================="
echo "Bot Trading Status Diagnostic"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if bot is running
echo "1. Checking if bot is running..."
BOT_STATUS=$(curl -s http://localhost:8000/api/bot/status 2>/dev/null)
if [ $? -eq 0 ]; then
    IS_RUNNING=$(echo $BOT_STATUS | grep -o '"is_running":[^,]*' | cut -d: -f2)
    PAPER_TRADING=$(echo $BOT_STATUS | grep -o '"paper_trading":[^,}]*' | cut -d: -f2)
    
    if [ "$IS_RUNNING" = "true" ]; then
        echo -e "${GREEN}✓ Bot is RUNNING${NC}"
    else
        echo -e "${RED}✗ Bot is NOT running${NC}"
        echo "   → Start bot via dashboard or: curl -X POST -u admin:admin http://localhost:8000/api/bot/start"
    fi
    
    if [ "$PAPER_TRADING" = "false" ]; then
        echo -e "${GREEN}✓ Paper trading is DISABLED (real trades enabled)${NC}"
    else
        echo -e "${RED}✗ Paper trading is ENABLED (only simulated trades)${NC}"
        echo "   → Disable via dashboard or API"
    fi
else
    echo -e "${RED}✗ Cannot connect to bot API${NC}"
    echo "   → Check if dashboard service is running: docker compose ps"
fi

echo ""

# 2. Check exchanges
echo "2. Checking exchanges..."
EXCHANGES=$(curl -s http://localhost:8000/api/exchanges/status 2>/dev/null)
if [ $? -eq 0 ]; then
    EXCHANGE_COUNT=$(echo $EXCHANGES | grep -o '"name"' | wc -l)
    CONNECTED_COUNT=$(echo $EXCHANGES | grep -o '"connected":true' | wc -l)
    
    echo "   Found $EXCHANGE_COUNT exchange(s), $CONNECTED_COUNT connected"
    
    if [ "$CONNECTED_COUNT" -lt 2 ]; then
        echo -e "${RED}✗ Need at least 2 connected exchanges for arbitrage${NC}"
        echo "   → Configure API keys in dashboard → Exchanges"
    else
        echo -e "${GREEN}✓ Sufficient exchanges connected${NC}"
    fi
else
    echo -e "${RED}✗ Cannot check exchanges${NC}"
fi

echo ""

# 3. Check trading pairs
echo "3. Checking trading pairs..."
PAIRS=$(curl -s http://localhost:8000/api/tokens/pairs 2>/dev/null)
if [ $? -eq 0 ]; then
    PAIR_COUNT=$(echo $PAIRS | grep -o '"symbol"' | wc -l)
    echo "   Found $PAIR_COUNT trading pair(s)"
    
    if [ "$PAIR_COUNT" -eq 0 ]; then
        echo -e "${RED}✗ No trading pairs configured${NC}"
        echo "   → Add pairs in dashboard → Tokens"
    else
        echo -e "${GREEN}✓ Trading pairs configured${NC}"
    fi
else
    echo -e "${RED}✗ Cannot check trading pairs${NC}"
fi

echo ""

# 4. Check opportunities
echo "4. Checking for opportunities..."
OPPORTUNITIES=$(curl -s http://localhost:8000/api/market/opportunities 2>/dev/null)
if [ $? -eq 0 ]; then
    OPP_COUNT=$(echo $OPPORTUNITIES | grep -o '"symbol"' | wc -l)
    echo "   Found $OPP_COUNT opportunity/ies"
    
    if [ "$OPP_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠ No opportunities detected right now${NC}"
        echo "   → This is normal if no market gaps exist"
        echo "   → Check prices: curl http://localhost:8000/api/market/prices"
    else
        echo -e "${GREEN}✓ Opportunities detected${NC}"
        # Show first opportunity
        echo "$OPPORTUNITIES" | head -c 200
        echo "..."
    fi
else
    echo -e "${RED}✗ Cannot check opportunities${NC}"
fi

echo ""

# 5. Check risk manager
echo "5. Checking risk manager..."
RISK=$(curl -s http://localhost:8000/api/risk/metrics 2>/dev/null)
if [ $? -eq 0 ]; then
    TRADING_ENABLED=$(echo $RISK | grep -o '"trading_enabled":[^,]*' | cut -d: -f2)
    EMERGENCY_STOP=$(echo $RISK | grep -o '"emergency_stop":[^,}]*' | cut -d: -f2)
    
    if [ "$TRADING_ENABLED" = "true" ]; then
        echo -e "${GREEN}✓ Trading is enabled${NC}"
    else
        echo -e "${RED}✗ Trading is DISABLED${NC}"
        echo "   → Enable in dashboard → Risk Management"
    fi
    
    if [ "$EMERGENCY_STOP" = "false" ]; then
        echo -e "${GREEN}✓ Emergency stop is NOT active${NC}"
    else
        echo -e "${RED}✗ Emergency stop is ACTIVE${NC}"
        echo "   → Reset in dashboard → Risk Management"
    fi
else
    echo -e "${RED}✗ Cannot check risk manager${NC}"
fi

echo ""

# 6. Check balances
echo "6. Checking balances..."
BALANCES=$(curl -s http://localhost:8000/api/portfolio/balances 2>/dev/null)
if [ $? -eq 0 ]; then
    BALANCE_COUNT=$(echo $BALANCES | grep -o '"exchange"' | wc -l)
    echo "   Found balances for $BALANCE_COUNT exchange(s)"
    
    if [ "$BALANCE_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠ No balances found${NC}"
        echo "   → This might be normal if API keys don't have balance permission"
    else
        echo -e "${GREEN}✓ Balances available${NC}"
    fi
else
    echo -e "${RED}✗ Cannot check balances${NC}"
fi

echo ""

# 7. Check recent logs
echo "7. Recent log activity (last 20 lines)..."
echo "   Looking for: opportunities, trades, errors"
docker compose logs dashboard --tail 20 2>/dev/null | grep -iE "opportunity|trade|execute|error|not allowed|not profitable" | tail -5

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "For detailed troubleshooting, see: docs/WHY_NO_TRADES.md"
echo ""
echo "Quick fixes:"
echo "1. If bot not running: Start via dashboard"
echo "2. If paper trading ON: Disable in dashboard"
echo "3. If < 2 exchanges: Add API keys in dashboard → Exchanges"
echo "4. If no pairs: Add pairs in dashboard → Tokens"
echo "5. If opportunities but no trades: Check risk manager and logs"
echo ""

