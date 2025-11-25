// Dashboard JavaScript
// Handles all frontend interactions and API calls

const API_BASE = window.location.origin;
let updateInterval = null;
let ws = null;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    connectWebSocket();
    loadInitialData();
    startPeriodicUpdates();
    
    // Show passphrase field for OKX
    document.getElementById('exchangeSelect').addEventListener('change', function() {
        const passphraseGroup = document.getElementById('passphraseGroup');
        if (this.value === 'okx') {
            passphraseGroup.style.display = 'block';
        } else {
            passphraseGroup.style.display = 'none';
        }
    });
    
    // Load configured exchanges list
    loadConfiguredExchanges();
});

// WebSocket connection for real-time updates
function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = function() {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'status_update') {
        updateBotStatus(data.data);
    } else if (data.type === 'bot_status') {
        showAlert('info', data.message);
        updateBotStatus({is_running: data.status === 'running'});
    } else if (data.type === 'alert') {
        showAlert(data.level, data.message);
    }
}

// Load initial data
async function loadInitialData() {
    await updateBotStatus();
    await loadTradingConfig();
    await loadRiskConfig();
}

// Start periodic updates
function startPeriodicUpdates() {
    updateInterval = setInterval(async function() {
        await updateBotStatus();
        await updateDashboardMetrics();
        
        // Update current tab content
        const activeTab = document.querySelector('.tab.active').textContent;
        if (activeTab.includes('Market')) {
            await loadMarketData();
        } else if (activeTab.includes('Opportunities')) {
            await loadOpportunities();
        } else if (activeTab.includes('Trade History')) {
            await loadTradeHistory();
        } else if (activeTab.includes('Balances')) {
            await loadBalances();
        }
    }, 5000); // Update every 5 seconds
}

// Bot control functions
async function startBot() {
    try {
        const response = await fetch(`${API_BASE}/api/bot/start`, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:admin')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('success', data.message);
            document.getElementById('btnStart').disabled = true;
            document.getElementById('btnStop').disabled = false;
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Failed to start bot: ' + error.message);
    }
}

async function stopBot() {
    try {
        const response = await fetch(`${API_BASE}/api/bot/stop`, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:admin')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('success', data.message);
            document.getElementById('btnStart').disabled = false;
            document.getElementById('btnStop').disabled = true;
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Failed to stop bot: ' + error.message);
    }
}

async function emergencyStop() {
    if (!confirm('Are you sure you want to trigger EMERGENCY STOP? This will halt all trading immediately.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/bot/emergency-stop`, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:admin')
            }
        });
        
        const data = await response.json();
        showAlert('error', data.message);
    } catch (error) {
        showAlert('error', 'Failed to trigger emergency stop: ' + error.message);
    }
}

// Update bot status
async function updateBotStatus(statusData) {
    try {
        if (!statusData) {
            const response = await fetch(`${API_BASE}/api/bot/status`);
            statusData = await response.json();
        }
        
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const btnStart = document.getElementById('btnStart');
        const btnStop = document.getElementById('btnStop');
        
        if (statusData.is_running) {
            statusDot.classList.add('running');
            statusText.textContent = 'Running';
            btnStart.disabled = true;
            btnStop.disabled = false;
            
            // Update uptime
            const hours = Math.floor(statusData.uptime_seconds / 3600);
            const minutes = Math.floor((statusData.uptime_seconds % 3600) / 60);
            const seconds = Math.floor(statusData.uptime_seconds % 60);
            document.getElementById('uptime').textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            document.getElementById('exchangesConnected').textContent = statusData.exchanges_connected || 0;
        } else {
            statusDot.classList.remove('running');
            statusText.textContent = 'Stopped';
            btnStart.disabled = false;
            btnStop.disabled = true;
            document.getElementById('uptime').textContent = '00:00:00';
        }
    } catch (error) {
        console.error('Error updating bot status:', error);
    }
}

// Update dashboard metrics
async function updateDashboardMetrics() {
    try {
        // Get risk metrics
        const riskResponse = await fetch(`${API_BASE}/api/risk/metrics`);
        const riskData = await riskResponse.json();
        
        if (!riskData.error) {
            document.getElementById('portfolioValue').textContent = 
                '$' + (riskData.portfolio_value || 0).toFixed(2);
            
            const dailyPnl = riskData.daily_pnl || 0;
            const dailyPnlElement = document.getElementById('dailyPnl');
            dailyPnlElement.textContent = '$' + dailyPnl.toFixed(2);
            dailyPnlElement.className = 'metric-value ' + (dailyPnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('drawdown').textContent = 
                (riskData.drawdown_percent || 0).toFixed(2) + '%';
        }
        
        // Get trading stats
        const statsResponse = await fetch(`${API_BASE}/api/trades/statistics`);
        const statsData = await statsResponse.json();
        
        if (!statsData.error) {
            document.getElementById('totalTrades').textContent = statsData.total_trades || 0;
            document.getElementById('winRate').textContent = 
                (statsData.success_rate || 0).toFixed(2) + '%';
            
            const totalProfit = statsData.total_profit_usd || 0;
            const totalProfitElement = document.getElementById('totalProfit');
            totalProfitElement.textContent = '$' + totalProfit.toFixed(2);
            totalProfitElement.className = 'metric-value ' + (totalProfit >= 0 ? 'positive' : 'negative');
        }
        
        // Get opportunities count
        const oppResponse = await fetch(`${API_BASE}/api/market/opportunities`);
        const oppData = await oppResponse.json();
        document.getElementById('opportunitiesFound').textContent = 
            oppData.opportunities ? oppData.opportunities.length : 0;
        
    } catch (error) {
        console.error('Error updating metrics:', error);
    }
}

// Load market data
async function loadMarketData() {
    try {
        const response = await fetch(`${API_BASE}/api/market/prices`);
        const data = await response.json();
        
        const container = document.getElementById('pricesContainer');
        
        if (data.error) {
            container.innerHTML = '<p class="alert alert-info">Bot not running. Start the bot to see market data.</p>';
            return;
        }
        
        if (Object.keys(data).length === 0) {
            container.innerHTML = '<p class="alert alert-info">No market data available yet. Please wait...</p>';
            return;
        }
        
        let html = '<div class="price-grid">';
        
        for (const [symbol, exchanges] of Object.entries(data)) {
            html += `<div class="price-card">
                <h3>${symbol}</h3>`;
            
            for (const [exchange, priceData] of Object.entries(exchanges)) {
                html += `<div class="exchange-price">
                    <span><strong>${exchange}:</strong></span>
                    <span>
                        B: $${priceData.bid.toFixed(4)} | 
                        A: $${priceData.ask.toFixed(4)}
                    </span>
                </div>`;
            }
            
            html += '</div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading market data:', error);
    }
}

// Load opportunities
async function loadOpportunities() {
    try {
        const response = await fetch(`${API_BASE}/api/market/opportunities`);
        const data = await response.json();
        
        const container = document.getElementById('opportunitiesContainer');
        
        if (data.opportunities.length === 0) {
            container.innerHTML = '<p class="alert alert-info">No arbitrage opportunities found yet.</p>';
            return;
        }
        
        let html = `<table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Symbol</th>
                    <th>Buy From</th>
                    <th>Sell To</th>
                    <th>Buy Price</th>
                    <th>Sell Price</th>
                    <th>Profit %</th>
                </tr>
            </thead>
            <tbody>`;
        
        data.opportunities.forEach(opp => {
            const time = new Date(opp.timestamp).toLocaleTimeString();
            const profitClass = opp.profit_percent >= 1 ? 'positive' : '';
            
            html += `<tr>
                <td>${time}</td>
                <td><strong>${opp.symbol}</strong></td>
                <td>${opp.buy_exchange}</td>
                <td>${opp.sell_exchange}</td>
                <td>$${opp.buy_price.toFixed(4)}</td>
                <td>$${opp.sell_price.toFixed(4)}</td>
                <td class="${profitClass}">${opp.profit_percent.toFixed(2)}%</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading opportunities:', error);
    }
}

// Load trade history
async function loadTradeHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/trades/history?limit=50`);
        const data = await response.json();
        
        const container = document.getElementById('tradesContainer');
        
        if (data.trades.length === 0) {
            container.innerHTML = '<p class="alert alert-info">No trades executed yet.</p>';
            return;
        }
        
        let html = `<table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Symbol</th>
                    <th>Buy From</th>
                    <th>Sell To</th>
                    <th>Amount</th>
                    <th>Profit (USD)</th>
                    <th>Profit %</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>`;
        
        data.trades.forEach(trade => {
            const time = new Date(trade.timestamp).toLocaleTimeString();
            const profitClass = trade.profit_usd >= 0 ? 'positive' : 'negative';
            
            html += `<tr>
                <td>${time}</td>
                <td><strong>${trade.symbol}</strong></td>
                <td>${trade.buy_exchange}</td>
                <td>${trade.sell_exchange}</td>
                <td>${trade.amount.toFixed(6)}</td>
                <td class="${profitClass}">$${trade.profit_usd.toFixed(2)}</td>
                <td class="${profitClass}">${trade.profit_percent.toFixed(2)}%</td>
                <td>${trade.status}</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading trade history:', error);
    }
}

// Load balances
async function loadBalances() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio/balances`);
        const data = await response.json();
        
        const container = document.getElementById('balancesContainer');
        
        if (data.error) {
            container.innerHTML = '<p class="alert alert-info">Bot not running. Start the bot to see balances.</p>';
            return;
        }
        
        if (Object.keys(data.balances).length === 0) {
            container.innerHTML = '<p class="alert alert-info">No balance data available yet.</p>';
            return;
        }
        
        let html = `<table>
            <thead>
                <tr>
                    <th>Asset</th>
                    <th>Total Amount</th>
                    <th>Value (USD)</th>
                    <th>Exchange Distribution</th>
                </tr>
            </thead>
            <tbody>`;
        
        for (const [asset, balance] of Object.entries(data.balances)) {
            const exchangeList = Object.entries(balance.exchanges)
                .map(([ex, amt]) => `${ex}: ${amt.toFixed(4)}`)
                .join(', ');
            
            html += `<tr>
                <td><strong>${asset}</strong></td>
                <td>${balance.total_amount.toFixed(6)}</td>
                <td>$${balance.total_value_usd.toFixed(2)}</td>
                <td>${exchangeList}</td>
            </tr>`;
        }
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading balances:', error);
    }
}

// Configuration functions
async function loadTradingConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config/trading`);
        const data = await response.json();
        
        document.getElementById('minProfitThreshold').value = data.min_profit_threshold;
        document.getElementById('maxTradeSize').value = data.max_trade_size_percent;
        document.getElementById('maxSlippage').value = data.max_slippage_percent;
    } catch (error) {
        console.error('Error loading trading config:', error);
    }
}

async function loadRiskConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config/risk`);
        const data = await response.json();
        
        document.getElementById('maxDrawdown').value = data.max_drawdown_percent;
        document.getElementById('maxDailyLoss').value = data.max_daily_loss_percent;
        document.getElementById('maxPositionSize').value = data.max_position_size_usd;
    } catch (error) {
        console.error('Error loading risk config:', error);
    }
}

function updateExchangeOptions() {
    const exchangeType = document.getElementById('exchangeType').value;
    const cexFields = document.getElementById('cexFields');
    const dexFields = document.getElementById('dexFields');
    const cexSelect = document.getElementById('cexExchangeSelect');
    const dexSelect = document.getElementById('dexExchangeSelect');
    
    if (exchangeType === 'cex') {
        cexFields.style.display = 'block';
        dexFields.style.display = 'none';
        cexSelect.style.display = 'block';
        dexSelect.style.display = 'none';
    } else {
        cexFields.style.display = 'none';
        dexFields.style.display = 'block';
        cexSelect.style.display = 'none';
        dexSelect.style.display = 'block';
    }
}

async function loadConfiguredExchanges() {
    try {
        const response = await fetch(`${API_BASE}/api/config/exchanges`);
        const data = await response.json();
        
        const container = document.getElementById('configuredExchangesList');
        
        if (!data.configured_exchanges || data.configured_exchanges.length === 0) {
            container.innerHTML = '<p style="color:#666;">No exchanges configured yet.</p>';
            return;
        }
        
        let html = '<h4>Configured Exchanges:</h4><table style="width:100%; margin-top:10px;"><thead><tr><th>Exchange</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
        
        data.configured_exchanges.forEach(ex => {
            const statusColor = ex.configured && ex.enabled ? '#2ecc71' : '#e74c3c';
            const statusText = ex.configured && ex.enabled ? '✅ Enabled' : ex.configured ? '⏸️ Disabled' : '❌ No Keys';
            
            html += `<tr>
                <td><strong>${ex.name}</strong></td>
                <td>${ex.type.toUpperCase()}</td>
                <td style="color:${statusColor}">${statusText}</td>
                <td>
                    <button class="btn-config" style="padding:5px 10px; font-size:12px;" onclick="toggleExchange('${ex.name}', ${!ex.enabled})">
                        ${ex.enabled ? 'Disable' : 'Enable'}
                    </button>
                </td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading configured exchanges:', error);
    }
}

async function toggleExchange(exchangeName, enabled) {
    try {
        const response = await fetch(`${API_BASE}/api/exchanges/toggle?exchange_name=${exchangeName}&enabled=${enabled}`, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa('admin:admin')
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showConfigAlert('exchange', 'success', data.message);
            loadConfiguredExchanges();
        } else {
            showConfigAlert('exchange', 'error', data.message);
        }
    } catch (error) {
        showConfigAlert('exchange', 'error', 'Failed to toggle: ' + error.message);
    }
}

async function saveExchangeConfig() {
    const exchangeType = document.getElementById('exchangeType').value;
    
    if (exchangeType === 'cex') {
        await saveCEXConfig();
    } else {
        await saveDEXConfig();
    }
}

async function saveCEXConfig() {
    const exchangeName = document.getElementById('exchangeSelect').value;
    const apiKey = document.getElementById('apiKey').value;
    const apiSecret = document.getElementById('apiSecret').value;
    const passphrase = document.getElementById('passphrase').value;
    const enabled = document.getElementById('enableExchange').checked;
    
    if (!apiKey || !apiSecret) {
        showConfigAlert('exchange', 'error', 'Please fill in all required fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/config/exchange`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa('admin:admin')
            },
            body: JSON.stringify({
                exchange_name: exchangeName,
                api_key: apiKey,
                api_secret: apiSecret,
                passphrase: passphrase || null,
                testnet: false,
                enabled: enabled
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showConfigAlert('exchange', 'success', data.message);
            // Clear fields
            document.getElementById('apiKey').value = '';
            document.getElementById('apiSecret').value = '';
            document.getElementById('passphrase').value = '';
            // Reload configured exchanges list
            loadConfiguredExchanges();
        } else {
            showConfigAlert('exchange', 'error', data.message);
        }
    } catch (error) {
        showConfigAlert('exchange', 'error', 'Failed to save: ' + error.message);
    }
}

async function saveDEXConfig() {
    const dexName = document.getElementById('dexSelect').value;
    const privateKey = document.getElementById('privateKey').value;
    const enabled = document.getElementById('enableDex').checked;
    
    if (!privateKey) {
        showConfigAlert('exchange', 'error', 'Please enter a private key');
        return;
    }
    
    // Validate private key format
    if (!privateKey.match(/^(0x)?[0-9a-fA-F]{64}$/)) {
        showConfigAlert('exchange', 'error', 'Invalid private key format');
        return;
    }
    
    showConfigAlert('exchange', 'info', 'DEX configuration coming soon...');
    // TODO: Implement DEX key saving
}

async function saveTradingConfig() {
    const minProfit = parseFloat(document.getElementById('minProfitThreshold').value);
    const maxTradeSize = parseFloat(document.getElementById('maxTradeSize').value);
    const maxSlippage = parseFloat(document.getElementById('maxSlippage').value);
    
    try {
        const response = await fetch(`${API_BASE}/api/config/trading`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa('admin:admin')
            },
            body: JSON.stringify({
                min_profit_threshold: minProfit,
                max_trade_size_percent: maxTradeSize,
                max_slippage_percent: maxSlippage,
                order_timeout_seconds: 30
            })
        });
        
        const data = await response.json();
        showConfigAlert('trading', data.status === 'success' ? 'success' : 'error', 
                       data.status === 'success' ? 'Configuration saved successfully' : data.detail);
    } catch (error) {
        showConfigAlert('trading', 'error', 'Failed to save: ' + error.message);
    }
}

async function saveRiskConfig() {
    const maxDrawdown = parseFloat(document.getElementById('maxDrawdown').value);
    const maxDailyLoss = parseFloat(document.getElementById('maxDailyLoss').value);
    const maxPositionSize = parseFloat(document.getElementById('maxPositionSize').value);
    
    try {
        const response = await fetch(`${API_BASE}/api/config/risk`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa('admin:admin')
            },
            body: JSON.stringify({
                max_drawdown_percent: maxDrawdown,
                max_daily_loss_percent: maxDailyLoss,
                max_position_size_usd: maxPositionSize,
                emergency_stop_enabled: true
            })
        });
        
        const data = await response.json();
        showConfigAlert('risk', data.status === 'success' ? 'success' : 'error', 
                       data.status === 'success' ? 'Configuration saved successfully' : data.detail);
    } catch (error) {
        showConfigAlert('risk', 'error', 'Failed to save: ' + error.message);
    }
}

// Utility functions
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Show selected tab
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        if (tab.textContent.toLowerCase().includes(tabName)) {
            tab.classList.add('active');
        }
    });
    
    const tabContent = document.getElementById(tabName + 'Tab');
    if (tabContent) {
        tabContent.classList.add('active');
        
        // Load tab data
        if (tabName === 'market') {
            loadMarketData();
        } else if (tabName === 'opportunities') {
            loadOpportunities();
        } else if (tabName === 'trades') {
            loadTradeHistory();
        } else if (tabName === 'balances') {
            loadBalances();
        }
    }
}

function showAlert(type, message) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // Add to control panel
    const controlPanel = document.querySelector('.control-panel');
    controlPanel.insertBefore(alert, controlPanel.firstChild);
    
    // Remove after 5 seconds
    setTimeout(() => alert.remove(), 5000);
}

function showConfigAlert(section, type, message) {
    const alertId = section + 'ConfigAlert';
    const alertElement = document.getElementById(alertId);
    
    alertElement.className = `alert alert-${type}`;
    alertElement.textContent = message;
    
    setTimeout(() => {
        alertElement.className = '';
        alertElement.textContent = '';
    }, 5000);
}

