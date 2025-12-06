# Modern Dashboard Architecture

## 🎯 Overview

The dashboard has been completely redesigned with a modern, scalable architecture using Next.js 14 App Router, TypeScript, and TailwindCSS.

## 📁 Project Structure

```
frontend/
├── app/
│   ├── dashboard/
│   │   ├── page.tsx          # Main dashboard overview
│   │   └── layout.tsx        # Dashboard layout wrapper
│   └── page.tsx              # Legacy redirect (preserved)
│
├── components/
│   ├── ui/                   # Reusable UI components
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Button.tsx
│   │   └── Skeleton.tsx
│   │
│   └── dashboard/            # Dashboard-specific components
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       ├── LiveTicker.tsx
│       └── MetricCard.tsx
│
└── hooks/                    # Custom React hooks
    ├── useBotStatus.ts
    ├── usePrices.ts
    └── useOpportunities.ts
```

## 🎨 Key Features

### 1. **Modern UI Components**
- **Card**: Flexible card component with variants (default, elevated, outlined)
- **Badge**: Status indicators with multiple variants
- **Button**: Consistent button styling with loading states
- **Skeleton**: Loading placeholders for better UX

### 2. **Custom Hooks**
- **useBotStatus**: Manages bot status with WebSocket integration
- **usePrices**: Real-time price updates with configurable refresh
- **useOpportunities**: Opportunity monitoring with auto-refresh

### 3. **Dashboard Components**
- **Sidebar**: Responsive navigation with mobile support
- **Header**: Sticky header with status indicators
- **LiveTicker**: Animated price ticker showing best opportunities
- **MetricCard**: Reusable metric display cards

## 🚀 Usage

### Accessing the Dashboard

The new dashboard is available at `/dashboard`. The root page (`/`) automatically redirects to `/dashboard`.

### Navigation

The sidebar provides access to:
- **Overview**: Main dashboard with key metrics
- **Market**: Market data and price charts
- **Opportunities**: Arbitrage opportunities
- **Trades**: Trade history
- **Balances**: Portfolio balances
- **Settings**: Configuration

## 🔄 Real-Time Updates

### WebSocket Integration
- Bot status updates via WebSocket
- Real-time price updates (configurable interval)
- Opportunity monitoring (5-second refresh)

### Polling Fallback
- Automatic fallback to HTTP polling if WebSocket fails
- Configurable refresh intervals per hook

## 📊 Dashboard Overview Features

1. **Live Ticker**: Scrolling display of best arbitrage opportunities
2. **Key Metrics**: Portfolio value, P&L, trades, opportunities
3. **Bot Status Card**: Current bot state and configuration
4. **Risk Metrics**: Drawdown, risk level, emergency stop status
5. **Recent Activity**: Best opportunity display

## 🎯 Best Practices

### Component Usage

```tsx
// Using Card component
<Card variant="elevated" padding="lg">
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    Content here
  </CardContent>
</Card>

// Using Badge
<Badge variant="success" size="md">Active</Badge>

// Using hooks
const { status, isLoading, error } = useBotStatus();
const { prices } = usePrices(false, 2000); // showAllPairs, refreshInterval
```

### Styling
- All components use TailwindCSS
- Dark theme optimized
- Responsive design (mobile-first)
- Smooth animations and transitions

## 🔧 Customization

### Adding New Routes

1. Create page in `app/dashboard/[route]/page.tsx`
2. Add navigation item in `Sidebar.tsx`
3. Use shared components and hooks

### Extending Hooks

Hooks can be extended with additional features:
- Error handling
- Retry logic
- Caching
- Optimistic updates

## 📝 Notes

- Legacy dashboard code preserved in `app/page.tsx` for reference
- All backend API endpoints remain unchanged
- TypeScript types maintained for type safety
- Performance optimized with proper React patterns

## 🚧 Future Enhancements

- [ ] Add more chart types
- [ ] Implement event log panel
- [ ] Add dark/light theme toggle
- [ ] Create settings panel component
- [ ] Add more dashboard widgets
- [ ] Implement data export features

