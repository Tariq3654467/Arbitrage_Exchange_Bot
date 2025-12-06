'use client';

import { useState } from 'react';
import { Shield, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface RiskControlsPanelProps {
  riskMetrics?: any;
  onEmergencyStop?: () => void;
  onUpdateRisk?: (config: any) => void;
}

export function RiskControlsPanel({
  riskMetrics,
  onEmergencyStop,
  onUpdateRisk
}: RiskControlsPanelProps) {
  const [maxDrawdown, setMaxDrawdown] = useState(riskMetrics?.max_drawdown_percent || 20);
  const [maxTradeSize, setMaxTradeSize] = useState(10);
  const [minProfit, setMinProfit] = useState(0.5);
  const [slippage, setSlippage] = useState(1.0);
  const [emergencyStopEnabled, setEmergencyStopEnabled] = useState(true);

  const handleSliderChange = (setter: (val: number) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setter(value);
    // Auto-save on change
    if (onUpdateRisk) {
      onUpdateRisk({
        max_drawdown_percent: maxDrawdown,
        max_trade_size_percent: maxTradeSize,
        min_profit_threshold: minProfit,
        max_slippage_percent: slippage
      });
    }
  };

  return (
    <div className="card-premium rounded-card p-6 space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-5 w-5 text-[#4ade80]" />
        <h3 className="text-lg font-semibold text-white">Risk Controls</h3>
      </div>

      {/* Emergency Stop Toggle */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">Emergency Stop</label>
          <button
            onClick={() => setEmergencyStopEnabled(!emergencyStopEnabled)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              emergencyStopEnabled ? 'bg-[#ef4444]' : 'bg-gray-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                emergencyStopEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Big Emergency Stop Button */}
        {onEmergencyStop && (
          <Button
            onClick={onEmergencyStop}
            className="w-full bg-[#ef4444] hover:bg-[#dc2626] text-white font-bold py-3 rounded-button shadow-lg hover:shadow-xl transition-all"
          >
            <AlertTriangle className="h-5 w-5 mr-2" />
            STOP ALL TRADES
          </Button>
        )}
      </div>

      <div className="h-px bg-[#1e293b]"></div>

      {/* Max Drawdown Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">Max Drawdown</label>
          <span className="text-sm font-semibold text-[#4ade80]">{maxDrawdown}%</span>
        </div>
        <input
          type="range"
          min="5"
          max="50"
          step="1"
          value={maxDrawdown}
          onChange={handleSliderChange(setMaxDrawdown)}
          className="w-full h-2 bg-[#1e293b] rounded-lg appearance-none cursor-pointer accent-[#4ade80]"
          style={{
            background: `linear-gradient(to right, #4ade80 0%, #4ade80 ${(maxDrawdown / 50) * 100}%, #1e293b ${(maxDrawdown / 50) * 100}%, #1e293b 100%)`
          }}
        />
      </div>

      {/* Max Trade Size Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">Max Trade Size</label>
          <span className="text-sm font-semibold text-[#60a5fa]">{maxTradeSize}%</span>
        </div>
        <input
          type="range"
          min="1"
          max="25"
          step="0.5"
          value={maxTradeSize}
          onChange={handleSliderChange(setMaxTradeSize)}
          className="w-full h-2 bg-[#1e293b] rounded-lg appearance-none cursor-pointer accent-[#60a5fa]"
          style={{
            background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${(maxTradeSize / 25) * 100}%, #1e293b ${(maxTradeSize / 25) * 100}%, #1e293b 100%)`
          }}
        />
      </div>

      {/* Min Profit Threshold Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">Min Profit Threshold</label>
          <span className="text-sm font-semibold text-[#38bdf8]">{minProfit}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="5"
          step="0.1"
          value={minProfit}
          onChange={handleSliderChange(setMinProfit)}
          className="w-full h-2 bg-[#1e293b] rounded-lg appearance-none cursor-pointer accent-[#38bdf8]"
          style={{
            background: `linear-gradient(to right, #38bdf8 0%, #38bdf8 ${(minProfit / 5) * 100}%, #1e293b ${(minProfit / 5) * 100}%, #1e293b 100%)`
          }}
        />
      </div>

      {/* Slippage Tolerance Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">Slippage Tolerance</label>
          <span className="text-sm font-semibold text-[#4ade80]">{slippage}%</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="5"
          step="0.1"
          value={slippage}
          onChange={handleSliderChange(setSlippage)}
          className="w-full h-2 bg-[#1e293b] rounded-lg appearance-none cursor-pointer accent-[#4ade80]"
          style={{
            background: `linear-gradient(to right, #4ade80 0%, #4ade80 ${(slippage / 5) * 100}%, #1e293b ${(slippage / 5) * 100}%, #1e293b 100%)`
          }}
        />
      </div>
    </div>
  );
}

