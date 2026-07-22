// Shared data-fetching helper + loading/error micro-components, reused
// across all portal tabs.
export const blank = () => ({ data: null, loading: true, error: false })

export async function load(apiFn, setter) {
  try {
    const r = await apiFn()
    if (!r.ok) throw new Error()
    setter({ data: await r.json(), loading: false, error: false })
  } catch {
    setter(s => ({ ...s, loading: false, error: true }))
  }
}
