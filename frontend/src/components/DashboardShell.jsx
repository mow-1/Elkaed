import { useState } from 'react'
import styles from './DashboardShell.module.css'

// Shared sidebar layout for the admin panel and student portal — same
// nav-shell component, each page just supplies its own sections/tabs.
// `sections`: [{ label?: string, items: [{ id, label, icon? }] }]
export default function DashboardShell({ title, sections, activeId, onSelect, children }) {
  const [open, setOpen] = useState(false)

  function handleSelect(id) {
    onSelect(id)
    setOpen(false)
  }

  return (
    <div className={styles.page}>
      <div className={styles.topRow}>
        <h1 className={styles.heading}>{title}</h1>
        <button
          className={styles.hamburger}
          onClick={() => setOpen(o => !o)}
          aria-label="فتح القائمة"
          aria-expanded={open}
        >
          {open ? '✕' : '☰'}
        </button>
      </div>

      <div className={styles.layout}>
        <nav className={`${styles.sidebar} ${open ? styles.sidebarOpen : ''}`}>
          {sections.map((section, i) => (
            <div key={i} className={styles.section}>
              {section.label && <p className={styles.sectionLabel}>{section.label}</p>}
              {section.items.map(item => (
                <button
                  key={item.id}
                  className={`${styles.navItem} ${activeId === item.id ? styles.navItemActive : ''}`}
                  onClick={() => handleSelect(item.id)}
                >
                  {item.icon && <span className={styles.navIcon}>{item.icon}</span>}
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        {open && <div className={styles.overlay} onClick={() => setOpen(false)} />}

        <div className={styles.content}>{children}</div>
      </div>
    </div>
  )
}
