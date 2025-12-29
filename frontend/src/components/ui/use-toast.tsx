import { useState } from "react"

type ToastProps = {
  title?: string
  description?: string
  variant?: "default" | "destructive"
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastProps[]>([])

  const toast = ({ title, description, variant }: ToastProps) => {
    console.log(`Toast: ${title} - ${description} (${variant})`)
    setToasts((prev) => [...prev, { title, description, variant }])
  }

  return {
    toast,
    toasts
  }
}
