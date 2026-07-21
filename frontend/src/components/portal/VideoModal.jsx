import { useEffect, useRef, useState } from 'react'
import { requestVideoToken } from '../../api/portal'
import styles from '../../pages/PortalPage.module.css'

// Shared video-launch mechanism reused by MaterialsTab / LessonsTab / MyCoursesTab.
// Safari plays HLS natively (canPlayType); every other browser needs hls.js to demux
// the .m3u8/.ts segments client-side — the AES-128 key is still fetched by hls.js
// itself from the key URI the playlist declares, same as native playback would.
export default function VideoModal({ lessonId, onClose }) {
  const [state, setState] = useState({ loading: true, error: '', data: null })
  const videoRef = useRef(null)
  const hlsRef = useRef(null)

  useEffect(() => {
    let alive = true
    requestVideoToken(lessonId)
      .then(async r => {
        const body = await r.json().catch(() => ({}))
        if (!alive) return
        if (!r.ok) { setState({ loading: false, error: body.detail || 'تعذّر تشغيل الفيديو', data: null }); return }
        setState({ loading: false, error: '', data: body })
      })
      .catch(() => alive && setState({ loading: false, error: 'تعذّر تشغيل الفيديو', data: null }))
    return () => { alive = false }
  }, [lessonId])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !state.data) return

    const url = state.data.hls_url

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url
      return
    }

    let cancelled = false
    import('hls.js').then(({ default: Hls }) => {
      if (cancelled) return
      if (!Hls.isSupported()) {
        setState(s => ({ ...s, error: 'المتصفح لا يدعم تشغيل هذا الفيديو' }))
        return
      }
      const hls = new Hls()
      hlsRef.current = hls
      hls.loadSource(url)
      hls.attachMedia(video)
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          setState(s => ({ ...s, error: 'تعذّر تشغيل الفيديو' }))
        }
      })
    })

    return () => {
      cancelled = true
      if (hlsRef.current) { hlsRef.current.destroy(); hlsRef.current = null }
    }
  }, [state.data])

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
        <button className={styles.modalClose} onClick={onClose}>✕</button>
        {state.loading && <p className={styles.loading}>جارٍ تجهيز الفيديو...</p>}
        {state.error && <p className={styles.errorRow}>{state.error}</p>}
        {state.data && (
          <>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video ref={videoRef} className={styles.videoPlayer} controls autoPlay />
            {state.data.views_remaining != null && (
              <p className={styles.viewsNote}>المشاهدات المتبقية: {state.data.views_remaining}</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
