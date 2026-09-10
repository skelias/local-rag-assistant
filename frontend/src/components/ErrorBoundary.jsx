import { Component } from 'react'

/** 错误边界：某个视图渲染出错时显示可读提示，而不是整页黑屏。 */
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'system-ui', color: '#f28b82', background: '#0f1115', minHeight: '100vh' }}>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>页面渲染出错</div>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#a2a9b4' }}>
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <button onClick={() => this.setState({ error: null })} style={{ marginTop: 16, padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(153,200,255,0.15)', color: '#99c8ff', cursor: 'pointer' }}>
            重试
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
