import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatView from './views/ChatView'
import KnowledgeView from './views/KnowledgeView'
import AgentView from './views/AgentView'
import SettingsView from './views/SettingsView'
import useStore from './store'

const views = {
  chat: ChatView,
  kb: KnowledgeView,
  agent: AgentView,
  settings: SettingsView,
}

export default function App() {
  const nav = useStore((s) => s.nav)
  const View = views[nav] || ChatView

  return (
    <div className="flex items-center justify-center h-screen p-5 pl-2 gap-3.5 overflow-hidden">
      {/* sidebar */}
      <Sidebar />

      {/* main panel */}
      <main className="glass-panel rounded-panel flex-1 max-w-[1100px] h-[calc(100vh-40px)] flex flex-col overflow-hidden relative">
        <TopBar />
        <div className="flex-1 min-h-0 overflow-hidden">
          <View />
        </div>
      </main>
    </div>
  )
}
