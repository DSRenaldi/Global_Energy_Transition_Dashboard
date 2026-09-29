import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  DatasetComponent,
  DataZoomComponent,
  GeoComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  TransformComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  DatasetComponent,
  DataZoomComponent,
  GeoComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  TransformComponent,
  CanvasRenderer,
])

export { echarts }

export function Chart({ option, className = '', ariaLabel }) {
  const elementRef = useRef(null)

  useEffect(() => {
    const chart = echarts.init(elementRef.current, null, { renderer: 'canvas' })
    chart.setOption(option, true)
    const resize = new ResizeObserver(() => chart.resize())
    resize.observe(elementRef.current)
    return () => {
      resize.disconnect()
      chart.dispose()
    }
  }, [option])

  return <div ref={elementRef} className={`chart ${className}`} role="img" aria-label={ariaLabel} />
}
