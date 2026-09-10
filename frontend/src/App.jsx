import { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatView from './views/ChatView'
import KnowledgeView from './views/KnowledgeView'
import AgentView from './views/AgentView'
import SettingsView from './views/SettingsView'
import useStore from './store'
import { api } from './api/client'

const views = {
  chat: ChatView,
  kb: KnowledgeView,
  agent: AgentView,
  settings: SettingsView,
}

const PRESET_BG = {
  'preset:default': '#0f1115',
  'preset:black': '#000000',
  'preset:navy': '#0a0e1a',
}

export default function App() {
  const nav = useStore((s) => s.nav)
  const profile = useStore((s) => s.profile)
  const setProfile = useStore((s) => s.setProfile)
  const View = views[nav] || ChatView

  // 启动拉取个性化配置（背景/头像）
  useEffect(() => {
    api.profile().then(setProfile).catch(() => {})
  }, [setProfile])

  // 应用背景（预设纯色 或 自定义图片 URL）
  useEffect(() => {
    const bg = profile.background
    document.body.style.backgroundImage = ''
    document.body.style.backgroundSize = 'cover'
    document.body.style.backgroundPosition = 'center'
    if (!bg || PRESET_BG[bg]) {
      document.body.style.backgroundColor = PRESET_BG[bg] || '#0f1115'
    } else {
      document.body.style.backgroundColor = '#0f1115'
      document.body.style.backgroundImage = `url(${bg})`
    }
  }, [profile.background])

  return (
    <div className="flex items-center justify-center h-screen p-5 pl-2 gap-3.5 overflow-hidden">
      {/* sidebar */}
      <Sidebar />

      {/* main panel：自定义背景图时更透，让背景透出来 */}
      <main className={`glass-panel rounded-panel flex-1 max-w-[1100px] h-[calc(100vh-40px)] flex flex-col overflow-hidden relative ${profile.background && !PRESET_BG[profile.background] ? 'faded' : ''}`}>
        <TopBar />
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <View />
        </div>
      </main>
    </div>
  )
}
