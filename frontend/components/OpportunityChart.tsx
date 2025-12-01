'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface OpportunityDataPoint {
  time: string;
  profit_percent: number;
  symbol?: string;
}

interface OpportunityChartProps {
  data: OpportunityDataPoint[];
  title: string;
}

export default function OpportunityChart({ data, title }: OpportunityChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No opportunities data available yet
      </div>
    );
  }

  return (
    <div className="w-full">
      <h4 className="mb-3 text-sm font-semibold text-slate-200">{title}</h4>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            }}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '11px' }}
            tickFormatter={(value) => `${value.toFixed(2)}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#e2e8f0',
            }}
            labelFormatter={(value) => new Date(value).toLocaleTimeString()}
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Profit']}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="profit_percent"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', r: 3 }}
            name="Profit %"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

