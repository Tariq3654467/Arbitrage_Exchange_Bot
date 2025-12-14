#!/bin/bash
# Verify Galaswap and bot status

echo "=========================================="
echo "Bot Status Check"
echo "=========================================="
echo ""

# 1. Check bot status
echo "1. Bot Status:"
curl -s http://localhost:8000/api/bot/status | python3 -m json.tool | grep -E "is_running|exchanges_connected|paper_trading"
echo ""

# 2. Check exchanges
echo "2. Exchanges Status:"
curl -s http://localhost:8000/api/config/exchanges | python3 -m json.tool | grep -A 5 "galaswap"
echo ""

# 3. Check if Galaswap prices are being fetched
echo "3. Checking for Galaswap prices (sample):"
curl -s http://localhost:8000/api/market/prices | python3 -c "import sys, json; data=json.load(sys.stdin); galaswap_pairs=[k for k in data.keys() if any('galaswap' in str(v) for v in data[k].values())]; print(f'Found {len(galaswap_pairs)} pairs with Galaswap prices'); [print(f'  - {p}') for p in list(galaswap_pairs)[:5]]" 2>/dev/null || echo "Checking prices..."
echo ""

# 4. Check opportunities
echo "4. Recent Opportunities:"
curl -s http://localhost:8000/api/market/opportunities | python3 -c "import sys, json; data=json.load(sys.stdin); opps=data.get('opportunities', []); print(f'Found {len(opps)} opportunities'); [print(f'  - {o.get(\"symbol\")}: {o.get(\"gross_profit_percent\", 0):.2f}% (Buy: {o.get(\"buy_exchange\")}, Sell: {o.get(\"sell_exchange\")})') for o in opps[:5]]" 2>/dev/null || echo "No opportunities yet"
echo ""

# 5. Check recent logs for errors
echo "5. Recent Galaswap Activity (last 10 lines):"
docker compose logs dashboard | grep -i galaswap | tail -10
echo ""

echo "=========================================="
echo "Status Summary"
echo "=========================================="
echo "If you see:"
echo "  ✓ exchanges_connected: 2 (Binance + Galaswap)"
echo "  ✓ Galaswap prices being fetched"
echo "  ✓ Opportunities detected"
echo ""
echo "Then everything is working! 🎉"

