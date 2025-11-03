import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Formats numbers with thousands separators and up to 2 decimals.
 * Falls back to string if invalid.
 * @param value number to format
 */
function formatNumber(value: number): string {
  if (typeof value !== 'number' || isNaN(value)) return String(value)
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  })
}

interface MetricsCardProps {
  title: string
  value: number | string
  unit?: string
  description?: string
  icon?: LucideIcon
  /**
   * Trend information for this metric.
   * - value: The magnitude of change (must be non-negative, e.g., 15.2 for "15.2% change")
   * - isPositive: The direction of the trend (true = improvement/increase, false = decline/decrease)
   */
  trend?: {
    value: number // Must be non-negative
    isPositive: boolean
  }
  className?: string
}

export function MetricsCard({
  title,
  value,
  unit = '',
  description,
  icon: Icon,
  trend,
  className,
}: MetricsCardProps) {
  const displayValue = typeof value === 'number' ? formatNumber(value) : value
  
  // Validate and normalize trend value to ensure it's non-negative
  const normalizedTrend = trend ? {
    ...trend,
    value: Math.abs(trend.value)
  } : undefined

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {displayValue}
          {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
        </div>
        {description && <CardDescription className="mt-1">{description}</CardDescription>}
        {normalizedTrend && (
          <p
            className={cn(
              'text-xs mt-1',
              normalizedTrend.isPositive ? 'text-green-600' : 'text-red-600'
            )}
          >
            <span aria-hidden="true">
              {normalizedTrend.isPositive ? '↑' : '↓'}
            </span>
            <span className="sr-only">
              {normalizedTrend.isPositive ? 'increased' : 'decreased'}
            </span>
            {' '}{normalizedTrend.value.toFixed(1)}% from baseline
          </p>
        )}
      </CardContent>
    </Card>
  )
}

