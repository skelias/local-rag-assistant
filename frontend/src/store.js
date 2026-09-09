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
}))

export default useStore
