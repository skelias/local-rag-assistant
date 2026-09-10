import { create } from 'zustand'

const useStore = create((set) => ({
  // navigation
  nav: 'chat',       // chat | kb | agent | settings
  setNav: (nav) => set({ nav }),

  // 当前知识库（1=默认全部 / 2=代码库 / 3=笔记库）
  kbId: 1,
  setKbId: (kbId) => set({ kbId }),

  // source drawer
  drawerOpen: false,
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),

  // active sources (for drawer)
  sources: [],
  setSources: (sources) => set({ sources }),

  // 个性化：背景 / 头像（值为 preset:xxx 或 /media/... URL）
  profile: { background: null, avatar_user: null, avatar_ai: null },
  setProfile: (profile) => set({ profile }),
}))

export default useStore
