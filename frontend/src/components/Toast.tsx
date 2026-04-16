import { useToast } from '../context/ToastContext'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
}

const tones = {
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  error: 'bg-rose-50 border-rose-200 text-rose-800',
  info: 'bg-sky-50 border-sky-200 text-sky-800',
}

const progressColors = {
  success: 'bg-emerald-400',
  error: 'bg-rose-400',
  info: 'bg-sky-400',
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => {
        const Icon = icons[toast.type]
        return (
          <div
            key={toast.id}
            className={`toast-enter rounded-2xl border px-4 py-3 shadow-card flex items-start gap-3 ${tones[toast.type]}`}
          >
            <Icon size={18} className="shrink-0 mt-0.5" />
            <p className="text-sm font-medium flex-1 leading-relaxed">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="opacity-40 hover:opacity-80 transition-opacity shrink-0 mt-0.5"
            >
              <X size={14} />
            </button>
            <div className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden rounded-b-2xl">
              <div
                className={`h-full toast-progress ${progressColors[toast.type]}`}
                style={{ animationDuration: `${toast.duration}ms` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
