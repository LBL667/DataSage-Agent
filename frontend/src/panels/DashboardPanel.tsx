import { useEffect, useState } from 'react'
import * as echarts from 'echarts'
import EChart from '../components/EChart'
import { getDashboardResults, getDashboardData, clearDashboard } from '../api/client'

interface Result {
  result_id: string
  title: string
  created_at: string
  result_ref?: string
  chart_spec?: { chart_type: string; x_field: string; y_field: string; series?: string; title?: string; description?: string }
  text?: string
}

const ACCENT = 'oklch(44% 0.12 258)'

export default function DashboardPanel() {
  const [results, setResults] = useState<Result[]>([])
  const [selected, setSelected] = useState<Result | null>(null)
  const [data, setData] = useState<{ columns: string[]; rows: unknown[][] } | null>(null)

  function refresh() {
    getDashboardResults().then((r) => {
      const list = (r.results as Result[]) || []
      setResults(list)
      if (!list.length) setSelected(null)
    })
  }

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (!selected?.result_ref) {
      setData(null)
      return
    }
    getDashboardData(selected.result_ref).then((d) => setData({ columns: d.columns, rows: d.rows }))
  }, [selected])

  async function onClear() {
    if (!confirm('确认清空所有分析结果？')) return
    await clearDashboard()
    refresh()
  }

  function chartOptions(): { title: string; option: echarts.EChartsOption }[] {
    if (!data || data.rows.length === 0) return []
    const spec = selected?.chart_spec
    const xIdx = spec ? data.columns.indexOf(spec.x_field) : 0
    const categoryCol = xIdx >= 0 ? xIdx : 0
    const x = data.rows.map((r) => String(r[categoryCol]))

    const numericCols = data.columns
      .map((c, i) => ({ name: c, idx: i }))
      .filter(({ idx }) => data.rows.every((r) => typeof r[idx] === 'number'))

    const charts: { title: string; option: echarts.EChartsOption }[] = []
    const base = {
      grid: { left: 48, right: 24, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: x, axisLabel: { interval: 0, rotate: 30 } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'var(--border)' } } },
      tooltip: { trigger: 'axis' },
    } as unknown as echarts.EChartsOption

    // 主图表：按 chart_spec 类型
    if (spec && spec.y_field) {
      const yIdx = data.columns.indexOf(spec.y_field)
      const y = data.rows.map((r) => Number(r[yIdx]))
      const label = spec.description || `${spec.y_field} 按 ${spec.x_field}`
      if (spec.chart_type === 'pie') {
        charts.push({
          title: label,
          option: { tooltip: { trigger: 'item' }, series: [{ type: 'pie', radius: '60%', data: x.map((name, i) => ({ name, value: y[i] })) }] } as unknown as echarts.EChartsOption,
        })
      } else {
        const kind = spec.chart_type === 'line' ? 'line' : 'bar'
        charts.push({
          title: label,
          option: { ...base, series: [{ type: kind, data: y, smooth: kind === 'line', itemStyle: { color: ACCENT }, lineStyle: { color: ACCENT } }] } as unknown as echarts.EChartsOption,
        })
      }
    }

    // 补充图表：其余数值列各出一个柱状图，实现多维度
    const usedY = spec?.y_field
    numericCols
      .filter((c) => c.name !== usedY)
      .slice(0, 4)
      .forEach((c) => {
        const y = data.rows.map((r) => Number(r[c.idx]))
        charts.push({
          title: `${c.name} 按 ${data.columns[categoryCol]}`,
          option: { ...base, series: [{ type: 'bar', data: y, itemStyle: { color: 'oklch(60% 0.1 258)' } }] } as unknown as echarts.EChartsOption,
        })
      })

    return charts
  }

  return (
    <div style={{ display: 'flex', gap: 20, height: '100%' }}>
      <div style={{ width: 300, flexShrink: 0, overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2>分析结果</h2>
          {results.length > 0 && (
            <button className="btn btn-ghost" style={{ height: 30, padding: '0 10px' }} onClick={onClear}>
              清空
            </button>
          )}
        </div>
        {results.length === 0 && <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)', fontSize: 14 }}>待生成</div>}
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

      <div style={{ flex: 1, minWidth: 0, overflow: 'auto' }}>
        {!selected && <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-muted)', fontSize: 14 }}>待生成</div>}
        {selected && (
          <div className="fade-up">
            <h2 style={{ marginBottom: 8 }}>{selected.title || '分析结果'}</h2>
            {selected.text && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20, maxWidth: '65ch' }}>{selected.text}</p>
            )}
            {chartOptions().map((c, i) => (
              <div key={i} className="card" style={{ padding: 16, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{c.title}</div>
                <EChart option={c.option} height={280} />
              </div>
            ))}
            {data && (
              <div className="card" style={{ padding: 16, overflow: 'auto' }}>
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
