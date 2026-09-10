import { create } from 'zustand'

const useStore = create((set) => ({
  // navigation
  nav: 'chat',       // chat | kb | agent | settings
  setNav: (nav) => set({ nav }),

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
