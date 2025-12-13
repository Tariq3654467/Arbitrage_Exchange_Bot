/**
 * Utility functions for formatting exchange names
 */

/**
 * Formats an exchange name for display
 * Converts exchange codes to properly formatted display names
 * 
 * @param exchange - Exchange code (e.g., "binance", "okx", "bybit")
 * @returns Formatted exchange name (e.g., "Binance", "OKX", "Bybit")
 */
export function formatExchangeName(exchange: string): string {
  if (!exchange) return exchange;
  
  const exchangeMap: Record<string, string> = {
    'binance': 'Binance',
    'okx': 'OKX',
    'okex': 'OKX',
    'bybit': 'Bybit',
    'mexc': 'MEXC',
    'galaswap': 'Galaswap',
    'pancakeswap': 'PancakeSwap',
    'uniswap': 'Uniswap',
    'uniswap_v2': 'Uniswap V2',
    'uniswap_v3': 'Uniswap V3',
  };
  
  const lowerExchange = exchange.toLowerCase();
  
  // Return mapped name if exists, otherwise capitalize first letter
  if (exchangeMap[lowerExchange]) {
    return exchangeMap[lowerExchange];
  }
  
  // Fallback: capitalize first letter of each word
  return exchange
    .split(/[_\s-]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

