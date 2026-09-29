import { useEffect, useState } from 'react'
import * as echarts from 'echarts'
import EChart from '../components/EChart'
import { getDashboardResults, getDashboardData } from '../api/client'

interface Result {
  result_id: string
  title: string
  created_at: string
  result_ref?: string
  chart_spec?: { chart_type: string; x_field: string; y_field: string; series?: string; title?: string }
  text?: string
}

export default function DashboardPanel() {
  const [results, setResults] = useState<Result[]>([])
  const [selected, setSelected] = useState<Result | null>(null)
  const [data, setData] = useState<{ columns: string[]; rows: unknown[][] } | null>(null)

  useEffect(() => {
    getDashboardResults().then((r) => setResults((r.results as Result[]) || []))
  }, [])

  useEffect(() => {
    if (!selected?.result_ref) return
    getDashboardData(selected.result_ref).then((d) => setData({ columns: d.columns, rows: d.rows }))
  }, [selected])

  function chartOption(res: Result): echarts.EChartsOption | null {
    const spec = res.chart_spec
    if (!spec || !data) return null
    const xIdx = data.columns.indexOf(spec.x_field)
    const yIdx = data.columns.indexOf(spec.y_field)
    if (xIdx < 0 || yIdx < 0) return null
    const x = data.rows.map((r) => String(r[xIdx]))
    const y = data.rows.map((r) => Number(r[yIdx]))
    const base = {
      grid: { left: 48, right: 24, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: 'var(--border)' } } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'var(--border)' } } },
      tooltip: { trigger: 'axis' },
    }
    if (spec.chart_type === 'bar') {
      return {
        ...base,
        series: [{ type: 'bar', data: y, itemStyle: { color: 'oklch(44% 0.12 258)' } }],
      } as unknown as echarts.EChartsOption
    }
    if (spec.chart_type === 'pie') {
      return {
        tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: '60%', data: x.map((name, i) => ({ name, value: y[i] })) }],
      } as unknown as echarts.EChartsOption
    }
    return {
      ...base,
      series: [{ type: 'line', data: y, smooth: true, lineStyle: { color: 'oklch(44% 0.12 258)' }, itemStyle: { color: 'oklch(44% 0.12 258)' } }],
    } as unknown as echarts.EChartsOption
  }

  return (
    <div style={{ display: 'flex', gap: 20, height: '100%' }}>
      {/* 结果列表 */}
      <div style={{ width: 300, flexShrink: 0, overflow: 'auto' }}>
        <h2 style={{ marginBottom: 16 }}>分析结果</h2>
        {results.length === 0 && <Empty text="还没有分析结果，去对话面板问一句" />}
        {results.map((r) => (
          <button
            key={r.result_id}
            onClick={() => setSelected(r)}
            className="card"
            style={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              padding: 14,
              marginBottom: 10,
              background: selected?.result_id === r.result_id ? 'var(--accent-soft)' : 'var(--surface)',
              borderColor: selected?.result_id === r.result_id ? 'var(--accent)' : 'var(--border)',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{r.title || '未命名'}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }} className="tabular">
              {r.created_at ? new Date(r.created_at).toLocaleString() : ''}
            </div>
          </button>
        ))}
      </div>

      {/* 详情 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {!selected && <Empty text="选择左侧结果查看图表" />}
        {selected && (
          <div className="fade-up">
            <h2 style={{ marginBottom: 8 }}>{selected.title || '分析结果'}</h2>
            {selected.text && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20, maxWidth: '65ch' }}>
                {selected.text}
              </p>
            )}
            {chartOption(selected) && <EChart option={chartOption(selected)!} />}
            {data && (
              <div className="card" style={{ padding: 16, marginTop: 20, overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {data.columns.map((c) => (
                        <th key={c} style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 500 }}>
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j} className="tabular" style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                            {String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)', fontSize: 14 }}>{text}</div>
  )
}
