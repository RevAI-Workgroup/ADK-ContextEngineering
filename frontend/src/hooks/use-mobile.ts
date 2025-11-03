import * as React from "react"

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    if (typeof window === 'undefined') return

    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(event.matches)
    }

    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handleChange)
    } else {
      mql.addListener(handleChange)
    }

    setIsMobile(mql.matches)

    return () => {
      if (typeof mql.removeEventListener === "function") {
        mql.removeEventListener("change", handleChange)
      } else {
        mql.removeListener(handleChange)
      }
    }
  }, [])

  return !!isMobile
}
